import unittest
import selectors
import time
import socket
from multiprocessing import Process
from multiprocessing import Manager

import securedrop.command as command

hostname = ''
port = 6969


def make_sock():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock


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
    def __init__(self, host: str, prt: int, sock, sel):
        super().__init__(host, prt, sock, sel, selectors.EVENT_READ | selectors.EVENT_WRITE)

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
        msg = b"a" * int(command.PACKET_MESSAGE_SIZE * 12.5) + b"b" * int(command.PACKET_MESSAGE_SIZE * 23)
        cmd = command.Command(hostname, port, None, None, selectors.EVENT_WRITE, b"name", msg)
        self.assertEqual(msg, cmd.conversation.outbound_packets.get_message())
        for i in range(36):
            self.assertEqual(cmd.conversation.outbound_packets.packets[i].header.index, i)
            self.assertEqual(cmd.conversation.outbound_packets.packets[i].header.total, 36)

    def test_command_echo(self):
        client_sel = selectors.DefaultSelector()
        server_sel = selectors.DefaultSelector()
        client_sock, server_sock = make_sock(), make_sock()
        cmd = command.Command(hostname, port, client_sock, client_sel, selectors.EVENT_READ | selectors.EVENT_WRITE,
                              b"echo",
                              b"data")
        recv = EchoServer(hostname, port, server_sock, server_sel)
        timer = Timer(5).start()
        server = None
        resp = [None]
        ex = False
        try:
            server = Process(target=recv.run, args=(timer.is_triggered,))
            server.start()
            time.sleep(1)
            cmd.run(timer.is_triggered, resp, 0)
        except Exception:
            ex = True
        finally:
            if server:
                server.terminate()
            client_sock.close()
            server_sock.close()
            client_sel.close()
            server_sel.close()

        self.assertFalse(ex)
        self.assertEqual(resp[0], b"data")

    def test_command_echo_concurrent(self):
        clients = 500
        client_sels = [selectors.DefaultSelector() for _ in range(clients)]
        server_sel = selectors.DefaultSelector()
        client_socks, server_sock = [make_sock() for _ in range(clients)], make_sock()
        cmds = [command.Command(hostname, port, client_socks[i], client_sels[i],
                                selectors.EVENT_READ | selectors.EVENT_WRITE,
                                b"echo",
                                b"data" + i.to_bytes(4, byteorder='little')) for i in range(clients)]
        recv = EchoServer(hostname, port, server_sock, server_sel)
        timer = Timer(10).start()
        manager = Manager()
        resps = manager.dict()
        server = None
        ex = False
        try:
            server = Process(target=recv.run, args=(timer.is_triggered,))
            server.start()
            time.sleep(1)
            client_threads = [Process(target=cmds[i].run, args=(timer.is_triggered, resps, i,)) for i in range(clients)]
            [client.start() for client in client_threads]
            [client.join() for client in client_threads]
        except Exception:
            ex = True
        finally:
            if server:
                server.terminate()
            [client_sock.close() for client_sock in client_socks]
            server_sock.close()
            [client_sel.close() for client_sel in client_sels]
            server_sel.close()

        self.assertFalse(ex)
        [self.assertEqual(resps[i], b"data" + i.to_bytes(4, byteorder='little')) for i in range(clients)]

    def test_command_echo_reuse_sock(self):
        num_reuses = 250
        client_sel = selectors.DefaultSelector()
        server_sel = selectors.DefaultSelector()
        client_sock, server_sock = make_sock(), make_sock()
        cmds = [command.Command(hostname, port, client_sock, client_sel, selectors.EVENT_READ | selectors.EVENT_WRITE,
                                b"echo",
                                b"data" + bytes([i])) for i in range(num_reuses)]
        recv = EchoServer(hostname, port, server_sock, server_sel)
        timer = Timer(5).start()
        server = None
        resp = [None] * num_reuses
        ex = False
        try:
            server = Process(target=recv.run, args=(timer.is_triggered,))
            server.start()
            time.sleep(1)
            for i in range(num_reuses):
                cmds[i].run(timer.is_triggered, resp, i)
        except Exception:
            ex = True
        finally:
            if server:
                server.terminate()
            client_sock.close()
            server_sock.close()
            client_sel.close()
            server_sel.close()

        self.assertFalse(ex)
        [self.assertEqual(resp[i], b"data" + bytes([i])) for i in range(num_reuses)]


if __name__ == '__main__':
    unittest.main()
