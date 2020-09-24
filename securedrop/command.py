import selectors

PacketDataSize = 1024
PacketHeaderElementSize = 4
PacketHeaderElements = 3
PacketHeaderSize = PacketHeaderElementSize * PacketHeaderElements
PacketMessageSize = PacketDataSize - PacketHeaderSize


class PacketHeader:
    def __init__(self, data: bytes = None, name: bytes = None, index: int = None, total: int = None):
        self.name = data[0:PacketHeaderElementSize] if data is not None else name
        self.index = int.from_bytes(data[PacketHeaderElementSize:2 * PacketHeaderElementSize], byteorder='little') if data is not None else index
        self.total = int.from_bytes(data[2 * PacketHeaderElementSize:3 * PacketHeaderElementSize], byteorder='little') if data is not None else total

        assert len(self.name) == PacketHeaderElementSize
        assert 0 <= self.index < self.total
        assert 0 <= self.total

    def __bytes__(self):
        return self.name + self.index.to_bytes(PacketHeaderElementSize, byteorder='little') + self.total.to_bytes(4, byteorder='little')


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


class Command:
    def __init__(self, host: str, port: str, sock, sel, events, name: bytes, message: bytes):
        self.sock = sock
        self.address = (host, port)
        self.sel = sel
        self.events = events
        self.outbound_packets = Packets(name=name, message=message)
        self.inbound_packets = Packets(name=name)
        self.is_complete = False

    def run(self):
        self.setup()
        return self.perform_command()

    def setup(self):
        self.sock.setblocking(False)
        self.sock.connect_ex(self.address)
        self.sel.register(self.sock, self.events, data=self.outbound_packets)

    def perform_command(self):
        while not self.is_complete:
            if events := self.sel.select(timeout=1):
                for _, mask in events:
                    self.service(mask)

        return self.inbound_packets.get_message()

    def service(self, mask):
        if mask & selectors.EVENT_READ:
            recv_data = self.sock.recv(PacketDataSize)
            if recv_data is not None:
                print("received", bytes(recv_data))
                packet = Packet(data=recv_data)
                self.inbound_packets.packets.append(packet)
                self.is_complete = packet.is_last
                if self.is_complete:
                    print("closing connection")
                    self.sel.unregister(self.sock)
                    self.sock.close()  # TODO: figure out if we should close here
        if mask & selectors.EVENT_WRITE:
            if self.outbound_packets.packets:
                print("sending", bytes(self.outbound_packets.packets[0]))
                self.sock.send(self.outbound_packets.packets.pop())
