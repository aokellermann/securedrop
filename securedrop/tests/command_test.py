import unittest
import selectors
import threading

import securedrop.command as command


class MockSocket:
    def __init__(self):
        self.connected_sock = None
        self.blocking = True
        self.address = ()
        self.lock = threading.Lock()
        self.data = None
        pass

    def setblocking(self, b: bool):
        self.blocking = b

    def connect_ex(self, addr):
        self.address = addr

    def close(self):
        del self.address

    def send(self, data: bytes):
        if self.address == self.connected_sock.address:
            with self.connected_sock.lock:
                self.connected_sock.data = data

    def recv(self, sz):
        with self.lock:
            data = self.data[:sz]
            self.data = self.data[sz:]
            return data


def make_socket_pair():
    sock1, sock2 = MockSocket(), MockSocket()
    sock1.connected_sock = sock2
    sock2.connected_sock = sock1
    return sock1, sock2


class MockSelector:
    def __init__(self):
        self.sockets = {}

    def register(self, sock, events, data=None):
        self.sockets[sock] = {"events": events, "data": data}

    def unregister(self, sock):
        del self.sockets[sock]

    def select(self, timeout=None):
        return [(sock, sock.events) for sock in self.sockets]


class MyTestCase(unittest.TestCase):
    def test_command_basic_ctor(self):
        cmd = command.Command("localhost", "6969", None, None, selectors.EVENT_WRITE, b"name", b"message")
        self.assertEqual(cmd.address, ("localhost", "6969"))
        self.assertEqual(cmd.events, selectors.EVENT_WRITE)
        self.assertEqual(len(cmd.outbound_packets.packets), 1)
        packet = cmd.outbound_packets.packets[0]
        self.assertEqual(packet.header.name, b"name")
        self.assertEqual(packet.header.index, 0)
        self.assertEqual(packet.header.total, 1)
        self.assertEqual(packet.message, b"message")
        self.assertTrue(packet.is_last)

    def test_command_multiple_packets(self):
        msg = b"a" * int(command.PacketMessageSize * 12.5) + b"b" * int(command.PacketMessageSize * 23)
        cmd = command.Command("localhost", "6969", None, None, selectors.EVENT_WRITE, b"name", msg)
        self.assertEqual(msg, cmd.outbound_packets.get_message())
        for i in range(36):
            self.assertEqual(cmd.outbound_packets.packets[i].header.index, i)
            self.assertEqual(cmd.outbound_packets.packets[i].header.total, 36)

    def test_mocksocket(self):
        sock1, sock2 = make_socket_pair()
        [sock.connect_ex(("localhost", "6969")) for sock in (sock1, sock2)]
        sock1.send(b"data")
        self.assertEqual(sock2.recv(4), b"data")
        sock2.send(b"resp")
        self.assertEqual(sock1.recv(4), b"resp")



if __name__ == '__main__':
    unittest.main()
