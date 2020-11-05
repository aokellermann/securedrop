from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.iostream import StreamClosedError
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
from multiprocessing import shared_memory


async def read(stream):
    data = await stream.read_until(b"\n\n")
    if len(data) >= 2 and data[len(data) - 2:] == b"\n\n":
        data = data[0:len(data) - 2]
    return data


async def write(stream, data: bytes):
    await stream.write(data + b"\n\n")


class ClientBase:
    def __init__(self, host, port, context=None):
        super().__init__()
        self.stream = None
        self.host = host
        self.port = port
        self.context = context

    def run(self, timeout):
        print("Client starting main loop")
        IOLoop.current().run_sync(self.main, timeout)
        print("Client exiting main loop")

    async def main(self):
        print("Client starting connection")
        self.stream = await TCPClient().connect('localhost', self.port, ssl_options=self.context)
        print("Client connected")

    async def read(self):
        data = await read(self.stream)
        print("Client read bytes: ", data[:80])
        return data

    async def write(self, data: bytes):
        await write(self.stream, data)
        print("Client wrote bytes: ", data[:80])


class ServerBase(TCPServer):
    def __init__(self):
        super().__init__()
        self.shm = None

    def run(self, port, shm_name):
        print("Server starting")
        self.shm = shared_memory.SharedMemory(shm_name)
        self.bind(port)
        self.start(0)
        print("Server starting main loop")
        PeriodicCallback(self.check_stop, 100).start()
        IOLoop.current().start()
        self.shm.close()
        self.shm = None
        print("Server exiting main loop")

    def check_stop(self):
        if self.shm.buf[0] == 1:
            IOLoop.current().add_callback(IOLoop.current().stop)

    async def handle_stream(self, stream, address):
        print("Server accepted connection")
        while True:
            try:
                data = await read(stream)
                print("Server read bytes: ", data[:80])
                await self.on_data_received(data, stream)
            except StreamClosedError:
                print("Server lost client at host ", address[0])
                break
            except Exception as e:
                print("Server caught exception: ", e)

    async def on_data_received(self, data, stream):
        pass

    async def write(self, stream, data: bytes):
        await write(stream, data)
        print("Server wrote bytes: ", data[:80])
