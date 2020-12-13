import ssl

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.iostream import StreamClosedError
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
from multiprocessing import shared_memory
from securedrop.utils import VerbosePrinter




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
        self.vprint = VerbosePrinter()

    def run(self, timeout=None):
        print("Client starting main loop")
        try:
            IOLoop.current().run_sync(self.main, timeout)
        finally:
            print("Client exiting main loop")

    async def main(self):
        print("Client starting connection")
        ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_ctx.load_verify_locations('server.pem')
        ssl_ctx.load_cert_chain('server.pem')
        ssl_ctx.check_hostname = False
        self.stream = await TCPClient().connect('127.0.0.1', self.port, ssl_options=ssl_ctx)
        print("Client connected")

    async def read(self):
        data = await read(self.stream)
        self.vprint.print("Client read bytes: ", data[:80])
        return data

    async def write(self, data: bytes):
        await write(self.stream, data)
        self.vprint.print("Client wrote bytes: ", data[:80])


class ServerBase(TCPServer):
    def __init__(self):
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain("server.pem")
        super().__init__(ssl_options=ssl_ctx)
        self.shm = None
        self.vprint = VerbosePrinter()

    def run(self, port, shm_name):
        print("Server starting")
        self.shm = shared_memory.SharedMemory(shm_name)
        self.listen(port)
        print("Server starting main loop")
        try:
            PeriodicCallback(self.check_stop, 100).start()
            IOLoop.current().start()
        finally:
            self.shm.close()
            self.shm = None
            print("Server exiting main loop")

    def check_stop(self):
        if self.shm.buf[0] == 1:
            IOLoop.current().add_callback(IOLoop.current().stop)

    async def handle_stream(self, stream, address):
        print("Server accepted connection at host ", address)
        await stream.wait_for_handshake()
        while True:
            try:
                data = await read(stream)
                self.vprint.print("Server read bytes: ", data[:80])
                await self.on_data_received(data, stream)
            except StreamClosedError:
                print("Server lost client at host ", address)
                await self.on_stream_closed(stream)
                break
            except Exception as e:
                print("Server caught exception: ", e)

    async def on_data_received(self, data, stream):
        pass

    async def on_stream_closed(self, address):
        pass

    async def write(self, stream, data: bytes):
        await write(stream, data)
        self.vprint.print("Server wrote bytes: ", data[:80])
