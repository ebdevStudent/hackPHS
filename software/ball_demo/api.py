import asyncio
import hmac
import json
import os
import secrets
import math
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, StreamingResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .engine import Engine
from .fixtures import trace
from .mission_control import MissionCommandRequest
from .sources import SCENARIOS


class OperatorRequest(BaseModel):
    # Operator intent must be explicit: do not coerce strings/bools into
    # commands or silently discard misspelled control fields.
    model_config = ConfigDict(strict=True, extra='forbid')


class SourceRequest(OperatorRequest):
    kind: str = 'synthetic'
    scenario: str = 'moving'
    path: str | None = None
    device: int = Field(default=0, ge=0, le=10)
    @model_validator(mode='after')
    def valid(self):
        if self.kind not in ['synthetic', 'recorded', 'camera']: raise ValueError('Invalid source kind')
        if self.scenario not in SCENARIOS: raise ValueError('Unknown scenario')
        if self.kind == 'recorded' and (not self.path or not Path(self.path).is_file()): raise ValueError('Recorded file must exist on the server')
        return self


class SettingsRequest(OperatorRequest):
    gain: float | None = Field(None, ge=0, le=2000)
    smoothing: float | None = Field(None, gt=0, le=1)
    deadband: float | None = Field(None, ge=0, le=.5)
    max_yaw: int | None = Field(None, ge=0, le=1000)
    slew_per_s: float | None = Field(None, gt=0, le=10000)
    direction: int | None = None
    hue_low: int | None = Field(None, ge=0, le=179)
    hue_high: int | None = Field(None, ge=0, le=179)
    saturation_min: int | None = Field(None, ge=0, le=255)
    value_min: int | None = Field(None, ge=0, le=255)
    min_area: int | None = Field(None, ge=1, le=50000)
    max_area: int | None = Field(None, ge=1, le=307200)
    target_mode: str | None = None
    tag_id: int | None = Field(None, ge=-1, le=586)
    tag_size_m: float | None = Field(None, ge=.01, le=2)
    camera_hfov_deg: float | None = Field(None, ge=40, le=220)
    land_range_m: float | None = Field(None, ge=.1, le=5)
    @model_validator(mode='after')
    def valid(self):
        if self.direction not in [None, -1, 1]: raise ValueError('Direction must be -1 or 1')
        if self.target_mode not in [None, 'color', 'tag', 'landing']: raise ValueError("target_mode must be 'color', 'tag' or 'landing'")
        return self


class AssistRequest(OperatorRequest):
    enabled: bool


class JudgeModeRequest(OperatorRequest):
    enabled: bool
    max_yaw: int | None = Field(None, ge=0, le=1000)


class JudgeYawRequest(OperatorRequest):
    pin: str = Field(min_length=1, max_length=12)
    yaw_pct: int = Field(ge=-100, le=100)


class FaultRequest(OperatorRequest):
    fault: str


class HeartbeatRequest(OperatorRequest):
    pass


class PickRequest(OperatorRequest):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    apply: bool = False


class NavigationRequest(OperatorRequest):
    action: str
    goal: list[float] | None = None
    heading_rad: float | None = None
    tag_id: int | None = Field(None, ge=0, lt=587)
    @model_validator(mode='after')
    def valid(self):
        if self.action not in ('goal', 'resume', 'disable', 'mission_start', 'mission_advance', 'mission_abort'):
            raise ValueError('Unknown navigation/mission action')
        if (self.action == 'goal') != (self.goal is not None): raise ValueError('Goal required only for goal action')
        if self.goal is not None and (len(self.goal) != 3 or not all(math.isfinite(x) for x in self.goal)): raise ValueError('Expected finite 3D metric goal')
        if self.action != 'goal' and (self.heading_rad is not None or self.tag_id is not None): raise ValueError('Goal heading/tag requires goal action')
        if self.heading_rad is not None and not -math.pi <= self.heading_rad <= math.pi: raise ValueError('Goal heading must be within ±π')
        return self


class NavigationBundleRequest(OperatorRequest):
    bundle: dict


class NavigationMissionRequest(OperatorRequest):
    mission: dict


def create_app(engine=None, token=None):
    engine = engine or Engine(os.environ.get('BALL_DATA_DIR', 'runs'))
    token = token or os.environ.get('BALL_OPERATOR_TOKEN') or secrets.token_urlsafe(24)
    @asynccontextmanager
    async def lifespan(app):
        engine.start()
        yield
        engine.stop()
    app = FastAPI(title='Ball Drone software demonstration', lifespan=lifespan)
    origins = [origin.strip().rstrip('/') for origin in
               os.environ.get('BALL_OPERATOR_ORIGINS', 'https://chessdroid108.github.io').split(',')
               if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=['GET', 'POST'],
                       allow_headers=['Authorization', 'Content-Type', 'X-Operator-Client'])
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Keep invalid NaN/Infinity input out of JSON error responses, too.
        def safe(value):
            if isinstance(value, float) and not math.isfinite(value): return str(value)
            if isinstance(value, dict): return {key: safe(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)): return [safe(item) for item in value]
            if isinstance(value, Exception): return str(value)
            return value
        return JSONResponse(status_code=422, content={'detail': safe(error.errors())})
    app.state.engine, app.state.operator_token = engine, token
    static = Path(__file__).parent / 'static'
    app.mount('/assets', StaticFiles(directory=static), name='assets')
    async def operator(authorization: str = Header(default='')):
        if not hmac.compare_digest(authorization, 'Bearer ' + token):
            raise HTTPException(401, 'Operator token required')
    @app.get('/')
    async def index(): return FileResponse(static / 'index.html')
    @app.get('/fallback')
    async def fallback(): return FileResponse(static / 'fallback.html')
    @app.get('/judge')
    async def judge_page(): return FileResponse(static / 'judge.html')
    @app.get('/api/judge/status')
    async def judge_status(): return engine.judge_snapshot()
    @app.post('/api/judge/yaw')
    async def judge_yaw(request: JudgeYawRequest):
        # Judges hold a PIN, not the operator token: it can only move the yaw slider.
        try: return engine.judge_command(request.pin, request.yaw_pct)
        except PermissionError as error: raise HTTPException(429 if 'Too many' in str(error) else 403, str(error))
        except ValueError as error: raise HTTPException(409, str(error))
    @app.get('/api/operator/judge', dependencies=[Depends(operator)])
    async def operator_judge(): return {**engine.judge_snapshot(), 'pin': engine.judge_pin}
    @app.post('/api/operator/judge', dependencies=[Depends(operator)])
    async def operator_judge_set(request: JudgeModeRequest):
        try: result = engine.set_judge_mode(request.enabled, request.max_yaw)
        except ValueError as error: raise HTTPException(409, str(error))
        return {**result, 'pin': engine.judge_pin}
    @app.get('/api/health')
    async def health():
        s = engine.snapshot()
        from . import __version__
        return {**engine.health(), 'service': 'ball-demo', 'version': __version__, 'state': s['state'], 'physical_output': False}
    @app.get('/api/state')
    async def state(): return engine.snapshot()
    @app.get('/api/mission/status')
    async def mission_status(): return engine.mission_status()
    @app.post('/api/operator/mission-commands', dependencies=[Depends(operator)])
    async def mission_command(request: MissionCommandRequest):
        try: return engine.submit_mission_command(request)
        except ValueError as error: raise HTTPException(409, str(error))
    @app.get('/api/operator/mission-commands/{request_id}', dependencies=[Depends(operator)])
    async def mission_command_status(request_id: str):
        result = engine.mission_command_result(request_id)
        if result is None: raise HTTPException(404, 'Unknown mission command request ID')
        return result
    @app.get('/api/navigation')
    async def navigation(): return engine.snapshot()['navigation']
    @app.get('/api/navigation/mission')
    async def navigation_mission():
        state = engine.snapshot()['navigation']
        return None if state is None else state.get('mission')
    @app.get('/api/navigation/map')
    async def navigation_map():
        return engine.navigation.bundle.map.model_dump() if engine.navigation else None
    @app.post('/api/operator/navigation', dependencies=[Depends(operator)])
    async def navigation_action(request: NavigationRequest):
        try: engine.navigation_command(request.action, request.goal, request.heading_rad, request.tag_id)
        except ValueError as error: raise HTTPException(409, str(error))
        return engine.snapshot()
    @app.post('/api/operator/navigation/bundle', dependencies=[Depends(operator)])
    async def navigation_bundle(request: NavigationBundleRequest):
        from .map_io import Bundle
        try:
            bundle = Bundle.model_validate(request.bundle)
            await asyncio.to_thread(engine.configure_navigation, bundle)
        except ValueError as error: raise HTTPException(422, str(error))
        return engine.snapshot()
    @app.post('/api/operator/navigation/mission', dependencies=[Depends(operator)])
    async def navigation_mission_upload(request: NavigationMissionRequest):
        from .mission import Mission
        try:
            mission = Mission.model_validate(request.mission)
            if engine.navigation is None: raise ValueError('Load a navigation bundle first')
            mission.validate_bundle(engine.navigation.bundle)
            await asyncio.to_thread(engine.configure_mission, mission)
        except ValueError as error: raise HTTPException(422, str(error))
        return engine.snapshot()
    @app.get('/api/preview.jpg')
    async def preview_frame():
        # Reuse the shared encoded frame for native clients; never re-encode per viewer.
        with engine.lock: frame = engine.preview
        if frame is None: return Response(status_code=204)
        return Response(frame, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})
    @app.get('/api/operator/roster', dependencies=[Depends(operator)])
    async def roster():
        return engine.roster_summary()
    @app.post('/api/operator/roster/reload', dependencies=[Depends(operator)])
    async def roster_reload():
        try: engine.reload_roster()
        except ValueError as error: raise HTTPException(409, str(error))
        return engine.roster_summary()
    @app.get('/api/operator/access', dependencies=[Depends(operator)])
    async def access(): return {'authorized': True}
    @app.get('/api/events')
    async def events():
        async def stream():
            while engine.running:
                yield 'data: ' + json.dumps(engine.snapshot()) + '\n\n'
                await asyncio.sleep(.1)
        return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-store'})
    @app.get('/api/preview')
    async def preview():
        async def stream():
            previous = -1
            while engine.running:
                with engine.lock: frame, index = engine.preview, engine.preview_index
                if frame is not None and index != previous:
                    previous = index
                    yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(frame)).encode() + b'\r\n\r\n' + frame + b'\r\n'
                await asyncio.sleep(.1)
        return StreamingResponse(stream(), media_type='multipart/x-mixed-replace; boundary=frame', headers={'Cache-Control': 'no-store'})
    @app.get('/api/scenarios')
    async def scenarios(): return SCENARIOS
    # Precompute once per scenario; no live bridge is reachable from trace generation.
    cache = {}
    # One trace generation at a time, so simultaneous visitors cannot load the processor
    # running live capture/control with several scenario computations at once.
    generation_lock = asyncio.Lock()
    @app.get('/api/sandbox/{scenario}')
    async def sandbox(scenario: str):
        if scenario not in SCENARIOS: raise HTTPException(404, 'Unknown scenario')
        if scenario not in cache:
            async with generation_lock:
                if scenario not in cache: cache[scenario] = await asyncio.to_thread(trace, scenario)
        return cache[scenario]
    @app.post('/api/operator/assist', dependencies=[Depends(operator)])
    async def assist(request: AssistRequest):
        # Browser/native operators hold a lease: if their heartbeats stop, assistance disables.
        try: engine.assist(request.enabled, leased=True)
        except ValueError as error: raise HTTPException(409, str(error))
        return engine.snapshot()
    @app.post('/api/operator/heartbeat', dependencies=[Depends(operator)])
    async def heartbeat(request: HeartbeatRequest):
        leased = engine.heartbeat()
        return {'leased': leased, 'lease_ms': engine.settings.lease_ms}
    @app.post('/api/operator/pick', dependencies=[Depends(operator)])
    async def pick(request: PickRequest):
        try: result = engine.pick_color(request.x, request.y, request.apply)
        except ValueError as error: raise HTTPException(409, str(error))
        result['snapshot'] = engine.snapshot()
        return result
    @app.post('/api/operator/source', dependencies=[Depends(operator)])
    async def source(request: SourceRequest):
        engine.set_source(request.model_dump(exclude_none=True))
        return engine.snapshot()
    @app.post('/api/operator/settings', dependencies=[Depends(operator)])
    async def settings(request: SettingsRequest):
        values = request.model_dump(exclude_none=True)
        candidate = {**engine.settings.dict(), **values}
        if candidate['hue_low'] > candidate['hue_high'] or candidate['min_area'] > candidate['max_area']:
            raise HTTPException(422, 'Lower threshold must not exceed upper threshold')
        engine.configure(values)
        return engine.snapshot()
    @app.post('/api/operator/fault', dependencies=[Depends(operator)])
    async def fault(request: FaultRequest):
        if request.fault not in ['none', 'disconnect', 'missing_ack', 'delayed_ack']: raise HTTPException(422, 'Unknown fault')
        try: engine.inject(request.fault)
        except ValueError as error: raise HTTPException(409, str(error))
        return engine.snapshot()
    @app.post('/api/operator/reset', dependencies=[Depends(operator)])
    async def reset():
        from .bridge import MockBridge
        if isinstance(engine.bridge, MockBridge): engine.inject('none')
        engine.set_source({'kind': 'synthetic', 'scenario': 'moving'})
        return engine.snapshot()
    from .ui_api import register_portable_routes
    app.state.portable_api = register_portable_routes(app, engine, token)
    return app
