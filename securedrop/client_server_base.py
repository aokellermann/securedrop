import ssl
import traceback

from logging import getLogger
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.iostream import StreamClosedError
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
from tornado.netutil import bind_sockets
from multiprocessing import shared_memory

MESSAGE_SENTINEL = b"\n" * 2

log = getLogger()


async def read(stream):
    data = await stream.read_until(MESSAGE_SENTINEL)
    if len(data) >= 2 and data[len(data) - 2:] == MESSAGE_SENTINEL:
        data = data[0:len(data) - 2]
    return data


async def write(stream, data: bytes):
    await stream.write(data + MESSAGE_SENTINEL)


class ClientBase:
    def __init__(self, host, port, server_cert_path="server.pem"):
        super().__init__()
        self.stream = None
        self.host = host
        self.port = port
        self.server_cert_path = server_cert_path

    def run(self, timeout=None):
        log.debug("Client starting main loop")
        try:
            IOLoop.current().run_sync(self.main, timeout)
        finally:
            log.debug("Client exiting main loop")

    async def main(self):
        log.debug("Client starting connection to {}".format((self.host, self.port)))
        ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if self.server_cert_path:
            ssl_ctx.load_verify_locations(self.server_cert_path)
            ssl_ctx.load_cert_chain(self.server_cert_path)
        ssl_ctx.check_hostname = False
        try:
            self.stream = await TCPClient().connect(self.host, self.port, ssl_options=ssl_ctx)
        except StreamClosedError:
            raise RuntimeError("Can't connect to server at {}".format((self.host, self.port)))
        log.debug("Client connected to {}".format((self.host, self.port)))

    async def read(self):
        data = await read(self.stream)
        log.debug("Client read bytes: {}".format(data[:80].rstrip(MESSAGE_SENTINEL)))
        return data

    async def write(self, data: bytes):
        await write(self.stream, data)
        log.debug("Client wrote bytes: {}".format(data[:80].rstrip(MESSAGE_SENTINEL)))


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
        print("Server listening on port(s) ", self.listen_ports)

    def run(self, port, shm_name):
        log.debug("Server starting")
        self.shm = shared_memory.SharedMemory(shm_name)

        # only listen() once!
        if not self.listen_ports:
            self.listen(port)

        log.debug("Server starting main loop")
        try:
            PeriodicCallback(self.check_stop, 100).start()
            IOLoop.current().start()
        except:
            # this is necessary because parent try/catch can't catch anything here for some reason
            raise
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
                log.debug("Server read bytes: {}".format(data[:80].rstrip(MESSAGE_SENTINEL)))
                await self.on_data_received(data, stream)
            except StreamClosedError:
                log.info("Server lost client at host {}".format(address))
                await self.on_stream_closed(stream, address)
                break
            except Exception as e:
                log.error("Server caught exception: {}".format(e))

    async def on_data_received(self, data, stream):
        pass

    async def on_stream_accepted(self, stream, address):
        pass

    async def on_stream_closed(self, stream, address):
        pass

    async def write(self, stream, data: bytes):
        await write(stream, data)
        log.debug("Server wrote bytes: {}".format(data[:80].rstrip(MESSAGE_SENTINEL)))
