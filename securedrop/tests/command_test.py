import unittest
import selectors
import time
from threading import Thread

import securedrop.command as command
import securedrop.utils as utils

hostname = ''
port = 6969


class EchoServer(command.CommandReceiver):
    def __init__(self, host: str, prt: int, sock, sel):
        super().__init__(host, prt, sock, sel, selectors.EVENT_READ | selectors.EVENT_WRITE)

    def on_command_received(self, conversation, sock):
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
        client_sock, server_sock = utils.make_sock(), utils.make_sock()
        cmd = command.Command(hostname, port, client_sock, client_sel, selectors.EVENT_READ | selectors.EVENT_WRITE,
                              b"echo",
                              b"data")
        recv = EchoServer(hostname, port, server_sock, server_sel)
        timer = utils.Timer(5).start()
        resp = [None]
        ex = False
        done = False
        server = None
        try:
            server = Thread(target=recv.run, args=(lambda: timer.is_triggered() or done,))
            server.start()
            time.sleep(1)
            cmd.run(timer.is_triggered, resp, 0)
        except Exception:
            ex = True
        finally:
            done = True
            if server:
                server.join()
            time.sleep(1)
            client_sock.close()
            server_sock.close()
            client_sel.close()
            server_sel.close()

        self.assertFalse(ex)
        self.assertEqual(resp[0], b"data")

    def test_command_echo_concurrent(self):
        clients = 100
        client_sels = [selectors.DefaultSelector() for _ in range(clients)]
        server_sel = selectors.DefaultSelector()
        client_socks, server_sock = [utils.make_sock() for _ in range(clients)], utils.make_sock()
        cmds = [command.Command(hostname, port, client_socks[i], client_sels[i],
                                selectors.EVENT_READ | selectors.EVENT_WRITE,
                                b"echo",
                                b"data" + i.to_bytes(4, byteorder='little')) for i in range(clients)]
        recv = EchoServer(hostname, port, server_sock, server_sel)
        timer = utils.Timer(30).start()
        resps = [None] * clients
        ex = False
        done = False
        server = None
        try:
            server = Thread(target=recv.run, args=(lambda: timer.is_triggered() or done,))
            server.start()
            time.sleep(1)
            client_threads = [Thread(target=cmds[i].run, args=(timer.is_triggered, resps, i,)) for i in range(clients)]
            [client.start() for client in client_threads]
            [client.join() for client in client_threads]
        except Exception:
            ex = True
        finally:
            done = True
            if server:
                server.join()
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
        client_sock, server_sock = utils.make_sock(), utils.make_sock()
        cmds = [command.Command(hostname, port, client_sock, client_sel, selectors.EVENT_READ | selectors.EVENT_WRITE,
                                b"echo",
                                b"data" + bytes([i])) for i in range(num_reuses)]
        recv = EchoServer(hostname, port, server_sock, server_sel)
        timer = utils.Timer(5).start()
        resp = [None] * num_reuses
        ex = False
        done = False
        server = None
        try:
            server = Thread(target=recv.run, args=(lambda: timer.is_triggered() or done,))
            server.start()
            time.sleep(1)
            for i in range(num_reuses):
                cmds[i].run(timer.is_triggered, resp, i)
        except Exception:
            ex = True
        finally:
            done = True
            if server:
                server.join()
            time.sleep(1)
            client_sock.close()
            server_sock.close()
            client_sel.close()
            server_sel.close()

        self.assertFalse(ex)
        [self.assertEqual(resp[i], b"data" + bytes([i])) for i in range(num_reuses)]


if __name__ == '__main__':
    unittest.main()
