import ssl

from logging import getLogger
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.iostream import StreamClosedError
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
from multiprocessing import shared_memory

log = getLogger()


async def read(stream):
    data = await stream.read_until(b"\n\n")
    if len(data) >= 2 and data[len(data) - 2:] == b"\n\n":
        data = data[0:len(data) - 2]
    return data


async def write(stream, data: bytes):
    await stream.write(data + b"\n\n")


class ClientBase:
    def __init__(self, host, port):
        super().__init__()
        self.stream = None
        self.host = host
        self.port = port

    def run(self, timeout=None):
        log.debug("Client starting main loop")
        try:
            IOLoop.current().run_sync(self.main, timeout)
        finally:
            log.debug("Client exiting main loop")

    async def main(self):
        log.debug("Client starting connection")
        ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_ctx.load_verify_locations('server.pem')
        ssl_ctx.load_cert_chain('server.pem')
        ssl_ctx.check_hostname = False
        self.stream = await TCPClient().connect('127.0.0.1', self.port, ssl_options=ssl_ctx)
        log.debug("Client connected")

    async def read(self):
        data = await read(self.stream)
        log.debug("Client read bytes: {}".format(data[:80]))
        return data

    async def write(self, data: bytes):
        await write(self.stream, data)
        log.debug("Client wrote bytes: {}".format(data[:80]))


class ServerBase(TCPServer):
    def __init__(self):
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain("server.pem")
        super().__init__(ssl_options=ssl_ctx)
        self.shm = None

    def run(self, port, shm_name):
        log.debug("Server starting")
        self.shm = shared_memory.SharedMemory(shm_name)
        self.listen(port)
        log.debug("Server starting main loop")
        try:
            PeriodicCallback(self.check_stop, 100).start()
            IOLoop.current().start()
        finally:
            self.shm.close()
            self.shm = None
            log.debug("Server exiting main loop")

    def check_stop(self):
        if self.shm.buf[0] == 1:
            IOLoop.current().add_callback(IOLoop.current().stop)

    async def handle_stream(self, stream, address):
        log.info("Server accepted connection at host {}".format(address))
        await stream.wait_for_handshake()
        while True:
            try:
                data = await read(stream)
                log.debug("Server read bytes: {}".format(data[:80]))
                await self.on_data_received(data, stream)
            except StreamClosedError:
                log.info("Server lost client at host {}".format(address))
                await self.on_stream_closed(stream)
                break
            except Exception as e:
                log.error("Server caught exception: {}".format(e))

    async def on_data_received(self, data, stream):
        pass

    async def on_stream_closed(self, address):
        pass

    async def write(self, stream, data: bytes):
        await write(stream, data)
        log.debug("Server wrote bytes: {}".format(data[:80]))
