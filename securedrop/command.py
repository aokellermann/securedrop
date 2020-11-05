import selectors
import socket
import socketserver
from threading import Lock
from typing import Any, Tuple, Callable

PACKET_DATA_SIZE = 1024
PACKET_HEADER_ELEMENT_SIZE = 4
PACKET_HEADER_ELEMENTS = 3
PACKET_HEADER_SIZE = PACKET_HEADER_ELEMENT_SIZE * PACKET_HEADER_ELEMENTS
PACKET_MESSAGE_SIZE = PACKET_DATA_SIZE - PACKET_HEADER_SIZE


class PacketHeader:
    def __init__(self, data: bytes = None, name: bytes = None, index: int = None, total: int = None):
        self.name = data[0:PACKET_HEADER_ELEMENT_SIZE] if data is not None else name
        self.index = int.from_bytes(data[PACKET_HEADER_ELEMENT_SIZE:2 * PACKET_HEADER_ELEMENT_SIZE],
                                    byteorder='little') if data is not None else index
        self.total = int.from_bytes(data[2 * PACKET_HEADER_ELEMENT_SIZE:3 * PACKET_HEADER_ELEMENT_SIZE],
                                    byteorder='little') if data is not None else total

    def __bytes__(self):
        return self.name + self.index.to_bytes(PACKET_HEADER_ELEMENT_SIZE, byteorder='little') + \
               self.total.to_bytes(4, byteorder='little')


class Packet:
    def __init__(self, data: bytes = None, name: bytes = None,
                 index: int = None, total: int = None, message: bytes = None):
        self.header = PacketHeader(data, name, index, total)
        self.message = data[PACKET_HEADER_SIZE:] if data is not None else message
        self.is_last = self.header.index == self.header.total - 1

    def __bytes__(self):
        return bytes(self.header) + self.message


class Packets:
    def __init__(self, data: bytes = None, name: bytes = None, message: bytes = None):
        if data is None and message is None:
            self.packets = []
            pass
        elif data is not None:
            self.packets = [Packet(data=data[i:i + PACKET_DATA_SIZE]) for i in range(0, len(data), PACKET_DATA_SIZE)]
        elif message is not None:
            self.packets = [Packet(name=name,
                                   index=int(i / PACKET_MESSAGE_SIZE),
                                   total=int(1 + len(message) / PACKET_MESSAGE_SIZE),
                                   message=message[i:i + PACKET_MESSAGE_SIZE]
                                   )
                            for i in range(0, len(message), PACKET_MESSAGE_SIZE)]

    def get_type(self):
        return self.packets[0].header.name if len(self.packets) != 0 else None

    def get_message(self):
        return b''.join([packet.message for packet in self.packets])


class ConversationData:
    def __init__(self):
        self.outbound_packets = Packets()
        self.inbound_packets = Packets()
        self.fully_received = False
        self.fully_sent = False
        self.is_complete = lambda: self.fully_received and self.fully_sent
        self.lock = Lock()

    def reset(self):
        self.outbound_packets = Packets()
        self.inbound_packets = Packets()
        self.fully_received = False
        self.fully_sent = False


class Command:
    def __init__(self, host: str, port: int, sock, sel, events, name: bytes = None, message: bytes = None,
                 packets: Packets = None):
        self.sock = sock
        self.address = (host, port)
        self.sel = sel
        self.events = events
        self.conversation = ConversationData()
        self.conversation.outbound_packets = Packets(name=name, message=message) if name and message else packets

    def run(self, sentinel, return_obj, return_obj_key):
        self.setup()
        self.select_until_complete(sentinel, return_obj, return_obj_key)

    def setup(self):
        self.sock.setblocking(False)
        self.sock.connect_ex(self.address)
        self.sel.register(self.sock, self.events)
        print("client connected to", self.address)

    def select_until_complete(self, sentinel, return_obj, return_obj_key):
        while not self.conversation.fully_received and not sentinel():
            if events := self.sel.select(timeout=1):
                for _, mask in events:
                    self.service(mask)

        return_obj[return_obj_key] = self.conversation.inbound_packets.get_message()
        if self.sock in self.sel.get_map():
            self.sel.unregister(self.sock)

    def service(self, mask):
        if mask & selectors.EVENT_READ:
            if recv_data := self.sock.recv(PACKET_DATA_SIZE):
                print("client received", bytes(recv_data))
                packet = Packet(data=recv_data)
                self.conversation.inbound_packets.packets.append(packet)
                self.conversation.fully_received = packet.is_last
        if mask & selectors.EVENT_WRITE:
            if self.conversation.outbound_packets.packets:
                out_packet = self.conversation.outbound_packets.packets.pop()
                self.conversation.fully_sent = out_packet.is_last
                self.sock.send(bytes(out_packet))
                print("client sending", bytes(out_packet))
        if self.conversation.is_complete():
            print("client command complete")
            self.sel.unregister(self.sock)  # Unregister, but don't close socket since it may be reused


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, server_address: Tuple[str, int],
                 RequestHandlerClass: Callable[..., socketserver.BaseRequestHandler], this):
        self.parent = this
        self.allow_reuse_address = True
        super().__init__(server_address, RequestHandlerClass)


class Handler(socketserver.BaseRequestHandler):
    def __init__(self, request: Any, client_address: Any, server: Server):
        self.conversation = ConversationData()
        self.parent = server
        super().__init__(request, client_address, server)

    def is_socket_closed(self):
        # https://stackoverflow.com/questions/48024720/python-how-to-check-if-socket-is-still-connected
        try:
            # this will try to read bytes without blocking and also without removing them from buffer (peek only)
            data = self.request.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
            if len(data) == 0:
                return True
        except BlockingIOError:
            return False  # socket is open and reading from it would block
        except ConnectionResetError:
            return True  # socket was closed for some other reason
        except Exception:
            return False
        return False

    def handle(self):
        while not self.is_socket_closed():
            if recv_data := self.request.recv(PACKET_DATA_SIZE):
                print("server received", bytes(recv_data))
                packet = Packet(data=recv_data)
                with self.conversation.lock:
                    self.conversation.inbound_packets.packets.append(packet)
                    self.conversation.fully_received = packet.is_last
                if self.conversation.fully_received:
                    self.parent.parent.on_command_received(self.conversation, self.request)
                else:
                    self.parent.parent.on_packet_received(self.conversation, self.request)
            if self.conversation.outbound_packets.packets:
                out_packet = self.conversation.outbound_packets.packets.pop()
                self.conversation.fully_sent = out_packet.is_last
                self.request.send(bytes(out_packet))
                print("server sending", bytes(out_packet))
            if self.conversation.is_complete():
                print("server conversation complete, resetting")
                with self.conversation.lock:  # Reset conversation, but don't unregister or close socket
                    self.conversation.reset()


class CommandReceiver:
    def __init__(self, host: str, port: int):
        self.address = (host, port)
        self.sock_serv = None

    def run(self):
        self.setup()
        return self.select_until_complete()

    def setup(self):
        self.sock_serv = Server(self.address, Handler, self)
        print("server listening on", self.address)

    def select_until_complete(self):
        with self.sock_serv:
            self.sock_serv.serve_forever()

    def shutdown(self):
        self.sock_serv.shutdown()

    def on_packet_received(self, conversation, sock):
        pass

    def on_command_received(self, conversation, sock):
        pass
