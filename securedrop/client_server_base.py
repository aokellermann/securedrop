import ssl
import traceback

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.iostream import StreamClosedError
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
from tornado.netutil import bind_sockets
from multiprocessing import shared_memory

MESSAGE_SENTINEL = b"\n" * 2


async def read(stream):
    data = await stream.read_until(MESSAGE_SENTINEL)
    if len(data) >= 2 and data[len(data) - 2:] == MESSAGE_SENTINEL:
        data = data[0:len(data) - 2]
    return data


async def write(stream, data: bytes):
    await stream.write(data + MESSAGE_SENTINEL)


class ClientBase:
    def __init__(self, host, port):
        super().__init__()
        self.stream = None
        self.host = host
        self.port = port
        self.server_cert_path = ""

    def run(self, timeout=None, server_cert_path="server.pem"):
        print("Client starting main loop")
        try:
            self.server_cert_path = server_cert_path
            IOLoop.current().run_sync(self.main, timeout)
        finally:
            print("Client exiting main loop")

    async def main(self):
        print("Client starting connection")
        ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if self.server_cert_path:
            ssl_ctx.load_verify_locations(self.server_cert_path)
            ssl_ctx.load_cert_chain(self.server_cert_path)
        ssl_ctx.check_hostname = False
        self.stream = await TCPClient().connect(self.host, self.port, ssl_options=ssl_ctx)
        print("Client connected")

    async def read(self):
        data = await read(self.stream)
        print("Client read bytes: ", data[:80].rstrip(MESSAGE_SENTINEL))
        return data

    async def write(self, data: bytes):
        await write(self.stream, data)
        print("Client wrote bytes: ", data[:80].rstrip(MESSAGE_SENTINEL))


class ServerBase(TCPServer):
    def __init__(self, cert_path="server.pem"):
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        if cert_path:
            ssl_ctx.load_cert_chain(cert_path)
        super().__init__(ssl_options=ssl_ctx)
        self.shm = None
        self.listen_ports = set()

    def listen(self, port: int, address: str = ""):
        # this essentially calls self.listen(port), but stores the listening ports for posterity
        socks = bind_sockets(port)
        self.add_sockets(socks)
        self.listen_ports = {sock.getsockname()[1] for sock in socks}

    def run(self, port, shm_name):
        print("Server starting")
        self.shm = shared_memory.SharedMemory(shm_name)

        # only listen() once!
        if not self.listen_ports:
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
        await self.on_stream_accepted(stream, address)

        await stream.wait_for_handshake()
        while True:
            try:
                data = await read(stream)
                print("Server read bytes: ", data[:80].rstrip(MESSAGE_SENTINEL))
                await self.on_data_received(data, stream)
            except StreamClosedError:
                print("Server lost client at host ", address)
                await self.on_stream_closed(stream, address)
                break
            except:
                print("Server caught exception: ")
                traceback.print_exc()

    async def on_data_received(self, data, stream):
        pass

    async def on_stream_accepted(self, stream, address):
        pass

    async def on_stream_closed(self, stream, address):
        pass

    async def write(self, stream, data: bytes):
        await write(stream, data)
        print("Server wrote bytes: ", data[:80].rstrip(MESSAGE_SENTINEL))
