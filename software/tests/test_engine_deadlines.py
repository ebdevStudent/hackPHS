"""Single control ticks on injected clocks: timeout priority and neutral output."""
import itertools
import json

import pytest
from ball_demo import engine as module
from ball_demo.engine import Engine
from ball_demo.sources import Frame


class TickBridge:
    transport='TEST / no physical output'
    fault='none'
    accepted_yaw=0
    def __init__(self,now):self.last_ack=now;self.seq=0;self.commands=[]
    def poll(self,now):return []
    def send(self,enabled,yaw,now):self.seq+=1;self.commands.append((enabled,yaw,now))
    def close(self):pass


@pytest.mark.parametrize('clock,age,kind,enabled',list(itertools.product(
    [.1,.111,1.1,10.1,10000.1],[249,250,251],['frame','ack','source','both'],[False,True])))
def test_control_tick_exact_timeouts_and_fault_priority(tmp_path,monkeypatch,clock,age,kind,enabled):
    monkeypatch.setattr(module.time,'monotonic',lambda:clock)
    bridge=TickBridge(clock)
    e=Engine(tmp_path,bridge=bridge);e.frame=Frame(None,clock,1,{})
    if kind in ['frame','both']:e.frame.captured=clock-age/1000
    if kind in ['ack','both']:bridge.last_ack=clock-age/1000
    if kind=='source':e.source_error='injected capture failure'
    e.detection={'error':.8};e.controller.enable(enabled)
    if enabled:e.controller.state='LOCKED';e.controller.yaw=300;e.controller.count=3
    e.running=True
    monkeypatch.setattr(module.time,'sleep',lambda duration:setattr(e,'running',False))
    e.control_loop()
    expected=('source: injected capture failure' if kind=='source' else
              ('stale frame' if kind in ['frame','both'] else 'missing acknowledgement') if age>=250 else None)
    if expected:
        assert e.controller.state=='FAULT' and e.controller.fault==expected
        assert not e.controller.enabled and e.controller.yaw==0 and bridge.commands[-1][:2]==(False,0)
    else:
        assert e.controller.fault is None and e.controller.enabled==enabled
        assert bridge.commands[-1][0]==enabled
        if not enabled:assert bridge.commands[-1][1]==0
    e.stop()
    events=[json.loads(v) for v in (e.session.path/'events.jsonl').read_text().splitlines()]
    faults=[v for v in events if v['type']=='fault']
    assert len(faults)==int(expected is not None)
    if faults:assert faults[0]['data']=={'reason':expected,'yaw':0}
    assert events[-1]['type']=='shutdown' and events[-1]['data']['yaw']==0


@pytest.mark.parametrize('clock,age',list(itertools.product([.1,.111,1.1,10.1,10000.1],[249,250,251])))
@pytest.mark.parametrize('kind',['frame','ack'])
def test_assist_enable_obeys_same_exact_deadline_as_control(tmp_path,monkeypatch,clock,age,kind):
    monkeypatch.setattr(module.time,'monotonic',lambda:clock)
    bridge=TickBridge(clock);e=Engine(tmp_path,bridge=bridge);e.frame=Frame(None,clock,1,{})
    if kind=='frame':e.frame.captured=clock-age/1000
    else:bridge.last_ack=clock-age/1000
    if age>=250:
        with pytest.raises(ValueError):e.assist(True)
        assert not e.controller.enabled and e.controller.yaw==0
    else:e.assist(True);assert e.controller.enabled and e.controller.state=='SEARCHING'
    e.stop()
