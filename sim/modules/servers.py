import threading


class RpcServer:
    def __init__(self, port: int):
        self.port = port
        self._thread: threading.Thread | None = None

    def start(self):
        # Scaffold: real server will be migrated later
        return

    def stop(self):
        return


class UartServer:
    def __init__(self, port: int):
        self.port = port

    def start(self):
        # Scaffold
        return

    def stop(self):
        return


class WebSocketServer:
    def __init__(self, port: int):
        self.port = port

    def start(self):
        # Scaffold
        return

    def stop(self):
        return
