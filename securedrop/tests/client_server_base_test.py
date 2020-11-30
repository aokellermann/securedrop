#!/usr/bin/env python

import time
from contextlib import contextmanager
import unittest
import os
from multiprocessing import Process, shared_memory

from tornado.testing import AsyncTestCase

from securedrop.client_server_base import ClientBase, ServerBase

HOSTNAME = "localhost"
PORT = 6969


class EchoClient(ClientBase):
    def __init__(self, data, response, start_index=0, end_index=None):
        super().__init__(HOSTNAME, PORT)
        self.data = data
        self.response = response
        self.start_index = start_index
        self.end_index = end_index

    async def main(self):
        await super().main()
        await self.write(self.data)
        if self.end_index is None:
            self.response[self.start_index] = await self.read()
        else:
            self.response[self.start_index:self.end_index] = await self.read()


class AsyncEchoClient(EchoClient):
    def __init__(self, data, sentinel_name, start_index, end_index):
        self.sentinel = shared_memory.SharedMemory(sentinel_name)
        super().__init__(data, self.sentinel.buf, start_index, end_index)

    async def main(self):
        try:
            await super().main()
        finally:
            self.sentinel.close()


class EchoServer(ServerBase):
    async def on_data_received(self, data, stream):
        await self.write(stream, data)


@contextmanager
def echo_server_process():
    sentinel = shared_memory.SharedMemory(create=True, size=1)
    sentinel.buf[0] = 0
    server = EchoServer()
    process = Process(target=server.run, args=(PORT, sentinel.name,))
    try:
        process.start()
        time.sleep(0.1)
        yield process
    finally:
        sentinel.buf[0] = 1
        process.join()
        sentinel.close()
        sentinel.unlink()


class EchoSingleThread(AsyncTestCase):
    def test_echo(self):
        with echo_server_process():
            for i in range(1, 27):
                with self.subTest(i=i):
                    response = [None]
                    data = os.urandom(2**i + i).replace(b'\n', b'')
                    EchoClient(data, response).run(30)
                    self.assertEqual(data, response[0])

    def test_echo_concurrent(self):
        clients_num = 200
        with echo_server_process():
            sentinel = shared_memory.SharedMemory(create=True, size=clients_num * 8)
            clients = [AsyncEchoClient(b"data" + i.to_bytes(4, byteorder='little'), sentinel.name, i * 8, i * 8 + 8) for i in range(clients_num)]
            threads = [Process(target=client.run, args=(30,)) for client in clients]
            for thread in threads:
                thread.daemon = True
                thread.start()
            for thread in threads:
                thread.join()
            for i in range(clients_num):
                self.assertEqual(b"data" + i.to_bytes(4, byteorder='little'), bytes(sentinel.buf[i * 8:i * 8 + 8]))
            sentinel.close()
            sentinel.unlink()


if __name__ == '__main__':
    unittest.main()
