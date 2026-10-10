"""Desktop-owned mock server in its own process, independent of native GUI work."""
import multiprocessing
import os
import secrets
import socket
from pathlib import Path


def run_server(data, token, host, port, listener, stop_event, parent_pid):
    import threading
    import uvicorn
    from .api import create_app
    from .engine import Engine

    engine = Engine(Path(data) / 'sessions')
    app = create_app(engine, token)

    def watch_parent():
        while not stop_event.wait(.2):
            if os.getppid() != parent_pid:
                stop_event.set()
                return
    threading.Thread(target=watch_parent, daemon=True).start()

    class ManagedServer(uvicorn.Server):
        async def on_tick(self, counter):
            if stop_event.is_set():
                engine.assist(False)
                return True
            return await super().on_tick(counter)

    config = uvicorn.Config(app, host=host, port=port, log_level='warning',
                            loop='asyncio', http='h11', ws='none', timeout_graceful_shutdown=1)
    ManagedServer(config).run(sockets=[listener])


class DesktopBackend:
    def __init__(self, data: Path, host='0.0.0.0', port=8080):
        data.mkdir(parents=True, exist_ok=True)
        self.data = data
        self.token = secrets.token_urlsafe(32)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for candidate in range(port, port + 10):
            try:
                self.socket.bind((host, candidate))
                break
            except OSError:
                if candidate == port + 9:
                    self.socket.close()
                    raise RuntimeError('No available demo port. Stop another instance or use --port.')
        self.socket.listen(128)
        self.port = self.socket.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        # Concurrent desktop sessions may share a data root but never a token file.
        self.token_path = data / f'operator-token-{self.port}'
        fd = os.open(self.token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(self.token)
        context = multiprocessing.get_context('spawn')
        self.stop_event = context.Event()
        self.process = context.Process(target=run_server,
                                       args=(str(data), self.token, host, self.port, self.socket, self.stop_event, os.getpid()))

    def start(self):
        self.process.start()

    def stop(self):
        # Server observes this independently of Qt/network and requests neutral.
        self.stop_event.set()
        if self.process.pid is not None:
            self.process.join(timeout=4)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=2)
        self.socket.close()
