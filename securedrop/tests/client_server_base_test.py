import time
from contextlib import contextmanager
import unittest
import os
from multiprocessing import Process, shared_memory

from tornado.testing import AsyncTestCase

from securedrop.client_server_base import ClientBase, ServerBase

#from tornado.testing import AsyncTestCase, gen_test

hostname = "localhost"
port = 6969


class EchoClient(ClientBase):
    def __init__(self, data, resp, start_index=0, end_index=None):
        super().__init__(hostname, port)
        self.data = data
        self.resp = resp
        self.start_index = start_index
        self.end_index = end_index

    async def main(self):
        await super().main()
        await self.write(self.data)
        if self.end_index is None:
            self.resp[self.start_index] = await self.read()
        else:
            self.resp[self.start_index:self.end_index] = await self.read()


class AsyncEchoClient(EchoClient):
    def __init__(self, data, shm_name, start_index, end_index):
        self.shm = shared_memory.SharedMemory(shm_name)
        super().__init__(data, self.shm.buf, start_index, end_index)

    async def main(self):
        try:
            await super().main()
        finally:
            self.shm.close()


class EchoServer(ServerBase):
    async def on_data_received(self, data, stream):
        await self.write(stream, data)


@contextmanager
def echo_server_process():
    shm = shared_memory.SharedMemory(create=True, size=1)
    shm.buf[0] = 0
    server = EchoServer()
    process = Process(target=server.run, args=(port, shm.name,))
    try:
        process.start()
        time.sleep(0.1)
        yield process
    finally:
        shm.buf[0] = 1
        process.join()
        shm.close()
        shm.unlink()


class EchoSingleThread(AsyncTestCase):
    def test_echo(self):
        with echo_server_process():
            for i in range(1, 2):
                with self.subTest(i=i):
                    resp = [None]
                    data = os.urandom(2**i + i).replace(b'\n\n', b'')
                    EchoClient(data, resp).run(3)
                    self.assertEqual(data, resp[0])

    def test_echo_concurrent(self):
        clients_num = 1
        with echo_server_process():
            shm = shared_memory.SharedMemory(create=True, size=clients_num * 8)
            clients = [AsyncEchoClient(b"data" + i.to_bytes(4, byteorder='little'), shm.name, i * 8, i * 8 + 8) for i in range(clients_num)]
            threads = [Process(target=client.run, args=(3,)) for client in clients]
            for thread in threads:
                thread.daemon = True
                thread.start()
            for thread in threads:
                thread.join()
            for i in range(clients_num):
                self.assertEqual(b"data" + i.to_bytes(4, byteorder='little'), bytes(shm.buf[i * 8:i * 8 + 8]))
            shm.close()
            shm.unlink()


if __name__ == '__main__':
    unittest.main()
