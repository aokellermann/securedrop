import selectors
from multiprocessing import Lock

PacketDataSize = 1024
PacketHeaderElementSize = 4
PacketHeaderElements = 3
PacketHeaderSize = PacketHeaderElementSize * PacketHeaderElements
PacketMessageSize = PacketDataSize - PacketHeaderSize


class PacketHeader:
    def __init__(self, data: bytes = None, name: bytes = None, index: int = None, total: int = None):
        self.name = data[0:PacketHeaderElementSize] if data is not None else name
        self.index = int.from_bytes(data[PacketHeaderElementSize:2 * PacketHeaderElementSize],
                                    byteorder='little') if data is not None else index
        self.total = int.from_bytes(data[2 * PacketHeaderElementSize:3 * PacketHeaderElementSize],
                                    byteorder='little') if data is not None else total

        # name_len = len(self.name)
        # assert name_len == PacketHeaderElementSize
        # assert 0 <= self.index < self.total
        # assert 0 <= self.total

    def __bytes__(self):
        return self.name + self.index.to_bytes(PacketHeaderElementSize, byteorder='little') + \
               self.total.to_bytes(4, byteorder='little')


class Packet:
    def __init__(self, data: bytes = None, name: bytes = None,
                 index: int = None, total: int = None, message: bytes = None):
        self.header = PacketHeader(data, name, index, total)
        self.message = data[PacketHeaderSize:] if data is not None else message
        self.is_last = self.header.index == self.header.total - 1

    def __bytes__(self):
        return bytes(self.header) + self.message


class Packets:
    def __init__(self, data: bytes = None, name: bytes = None, message: bytes = None):
        if data is None and message is None:
            self.packets = []
            pass
        elif data is not None:
            self.packets = [Packet(data=data[i:i + PacketDataSize]) for i in range(0, len(data), PacketDataSize)]
        elif message is not None:
            self.packets = [Packet(name=name,
                                   index=int(i / PacketMessageSize),
                                   total=int(1 + len(message) / PacketMessageSize),
                                   message=message[i:i + PacketMessageSize]
                                   )
                            for i in range(0, len(message), PacketMessageSize)]

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


class Command:
    def __init__(self, host: str, port: int, sock, sel, events, name: bytes, message: bytes):
        self.sock = sock
        self.address = (host, port)
        self.sel = sel
        self.events = events
        self.conversation = ConversationData()
        self.conversation.outbound_packets = Packets(name=name, message=message)
        self.response = b""

    def run(self, sentinel):
        self.setup()
        return self.select_until_complete(sentinel)

    def setup(self):
        self.sock.setblocking(False)
        self.sock.connect_ex(self.address)
        self.sel.register(self.sock, self.events)
        print("client connected to", self.address)

    def select_until_complete(self, sentinel):
        while not self.conversation.fully_received and not sentinel():
            if events := self.sel.select(timeout=1):
                for _, mask in events:
                    self.service(mask)

        self.response = self.conversation.inbound_packets.get_message()
        return self.response

    def service(self, mask):
        if mask & selectors.EVENT_READ:
            recv_data = self.sock.recv(PacketDataSize)
            if recv_data is not None:
                print("client received", bytes(recv_data))
                packet = Packet(data=recv_data)
                self.conversation.inbound_packets.packets.append(packet)
                self.conversation.fully_received = packet.is_last
                if self.conversation.fully_received:
                    print("client closing connection")
                    self.sel.unregister(self.sock)
                    self.sock.close()  # TODO: figure out if we should close here
        if mask & selectors.EVENT_WRITE:
            if self.conversation.outbound_packets.packets:
                print("client sending", bytes(self.conversation.outbound_packets.packets[0]))
                self.sock.send(bytes(self.conversation.outbound_packets.packets.pop()))


class CommandReceiver:
    def __init__(self, host: str, port: int, sock, sel, events):
        self.address = (host, port)
        self.sock = sock
        self.sel = sel
        self.events = events

    def run(self, sentinel):
        self.setup()
        return self.select_until_complete(sentinel)

    def setup(self):
        self.sock.bind(self.address)
        self.sock.listen()
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ, data=None)
        print("server listening on", self.address)

    def select_until_complete(self, sentinel):
        while not sentinel():
            events = self.sel.select(timeout=1)
            for key, mask in events:
                if key.data is None:
                    sock = key.fileobj
                    conn, addr = sock.accept()
                    print("server accepted connection from", addr)
                    conn.setblocking(False)
                    self.sel.register(conn, self.events, data=ConversationData())
                else:
                    self.service(key, mask)

    def service(self, key, mask):
        sock = key.fileobj
        conversation = key.data
        if mask & selectors.EVENT_READ:
            if recv_data := sock.recv(PacketDataSize):
                print("server received", bytes(recv_data))
                packet = Packet(data=recv_data)
                with conversation.lock:
                    conversation.inbound_packets.packets.append(packet)
                    conversation.fully_received = packet.is_last
                if conversation.fully_received:
                    self.on_command_received(conversation)
                else:
                    self.on_packet_received(conversation)
        if mask & selectors.EVENT_WRITE:
            if conversation.outbound_packets.packets:
                out_packet = conversation.outbound_packets.packets.pop()
                conversation.fully_sent = out_packet.is_last
                sock.send(bytes(out_packet))
                print("server sending", bytes(out_packet))
        if conversation.is_complete():
            print("server closing connection")
            self.sel.unregister(sock)
            sock.close()

    def on_packet_received(self, conversation):
        pass

    def on_command_received(self, conversation):
        pass
