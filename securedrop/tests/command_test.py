import unittest
import selectors
import threading
import time
import socket
from multiprocessing import Process

import securedrop.command as command

hostname = ''
port = 6969


class Timer:
    def __init__(self, duration):
        self.duration = duration
        self.begin = None

    def start(self):
        self.begin = time.time()
        return self

    def is_triggered(self):
        return time.time() - self.begin - self.duration >= 0


class EchoServer(command.CommandReceiver):
    def on_command_received(self, conversation):
        with conversation.lock:
            msg = conversation.inbound_packets.get_message()
            packets = command.Packets(name=b"echo", message=msg)
            conversation.outbound_packets = packets


class MyTestCase(unittest.TestCase):
    def test_command_basic_ctor(self):
        cmd = command.Command(hostname, port, None, None, selectors.EVENT_WRITE, b"name", b"message")
        self.assertEqual(cmd.address, (hostname, 6969))
        self.assertEqual(cmd.events, selectors.EVENT_WRITE)
        self.assertEqual(len(cmd.conversation.outbound_packets.packets), 1)
        packet = cmd.conversation.outbound_packets.packets[0]
        self.assertEqual(packet.header.name, b"name")
        self.assertEqual(packet.header.index, 0)
        self.assertEqual(packet.header.total, 1)
        self.assertEqual(packet.message, b"message")
        self.assertTrue(packet.is_last)
        self.assertFalse(cmd.conversation.fully_sent)
        self.assertFalse(cmd.conversation.fully_received)
        self.assertFalse(cmd.conversation.is_complete())

    def test_command_multiple_packets(self):
        msg = b"a" * int(command.PacketMessageSize * 12.5) + b"b" * int(command.PacketMessageSize * 23)
        cmd = command.Command(hostname, port, None, None, selectors.EVENT_WRITE, b"name", msg)
        self.assertEqual(msg, cmd.conversation.outbound_packets.get_message())
        for i in range(36):
            self.assertEqual(cmd.conversation.outbound_packets.packets[i].header.index, i)
            self.assertEqual(cmd.conversation.outbound_packets.packets[i].header.total, 36)

    def test_command_echo(self):
        sel1 = selectors.DefaultSelector()
        sel2 = selectors.DefaultSelector()
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        cmd = command.Command(hostname, port, sock1, sel1, selectors.EVENT_READ | selectors.EVENT_WRITE, b"echo",
                              b"data")
        recv = EchoServer(hostname, port, sock2, sel2, selectors.EVENT_READ | selectors.EVENT_WRITE)
        timer = Timer(5).start()
        server = None
        resp = None
        ex = False
        try:
            server = Process(target=recv.run, args=(timer.is_triggered,))
            server.start()
            time.sleep(1)
            resp = cmd.run(timer.is_triggered)
        except Exception:
            ex = True
        finally:
            sock1.close()
            sock2.close()
            sel1.close()
            sel2.close()
            if server:
                server.terminate()

        self.assertFalse(ex)
        self.assertEqual(resp, b"data")


if __name__ == '__main__':
    unittest.main()
