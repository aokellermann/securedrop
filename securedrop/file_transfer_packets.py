import json

# ****************************************************************

# Key

# X: client #1 (sender)
# Y: client #2 (recipient)
# S: server
# F: file

# Part 1: P2P Facilitation

# 1. `X -> Y/F -> S`: X wants to send F to Y
# 2. `Y -> S`: every one second, Y asks server for any requests
# 3. `S -> X/F -> Y`: server responds with active requests
# 4. `Y -> Yes/No -> S`: Y accepts or denies transfer request
# 5(a). `S -> X -> Y, S -> Y -> X`: if Y accepted, server sends X's IP address to Y and server sends Y's IP address to X
# 5(b). `S -> Deny -> X`: if Y denied, server notifies X of denial
# 6(a). `Y listens for X`: if Y accepted, Y listens for X
# 6(b). `X connects to Y`: if Y accepted, X connects to Y

# Part 2: Transfer Protocol

# 1. `X -> Hash(F)/Chunks(F) -> Y`: X sends the hash of F and the number of chunks in F to Y
# 2. `X -> NextChunk(F) -> Y`: X sends next chunk of file to Y
# 3. `Y -> Success/Failure -> X`: after all chunks received, Y sends success/failure to X

# ****************************************************************


# Part 1: P2P Facilitation

# 1. `X -> Y/F -> S`: X wants to send F to Y


FILE_TRANSFER_REQUEST_TRANSFER_PACKETS_NAME = b"FTRP"


class FileTransferRequestPackets:
    def __init__(self, recipient_email: str = None, file_info: dict = None, data=None):
        self.recipient_email, self.file_info = recipient_email, file_info
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.recipient_email, self.file_info = self.jdict["recipient_email"], self.jdict["file_info"]
        elif recipient_email is not None and file_info is not None:
            self.jdict = {
                "recipient_email": self.recipient_email,
                "requests": self.file_info,
            }

    def __bytes__(self):
        return FILE_TRANSFER_REQUEST_TRANSFER_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# 2. `Y -> S`: every one second, Y asks server for any requests

FILE_TRANSFER_CHECK_REQUESTS_PACKETS_NAME = b"FTCR"


class FileTransferRequestResponsePackets:
    def __bytes__(self):
        return FILE_TRANSFER_CHECK_REQUESTS_PACKETS_NAME


# 3. `S -> X/F -> Y`: server responds with active requests

FILE_TRANSFER_CHECK_REQUESTS_RESPONSE_PACKETS_NAME = b"FTRR"


class FileTransferCheckRequestsPackets:
    def __init__(self, requests: dict = None, data=None):
        self.requests = requests
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.requests = self.jdict["requests"]
        elif requests is not None:
            self.jdict = {
                "requests": self.requests,
            }

    def __bytes__(self):
        return FILE_TRANSFER_CHECK_REQUESTS_RESPONSE_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# 4. `Y -> Yes/No -> S`: Y accepts or denies transfer request

FILE_TRANSFER_ACCEPT_REQUEST_PACKETS_NAME = b"FTAR"


class FileTransferAcceptRequestPackets:
    def __init__(self, sender_email: str = None, data=None):
        # If email is empty string, the request was denied.
        self.sender_email = sender_email
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.sender_email = self.jdict["sender_email"]
        elif sender_email is not None:
            self.jdict = {
                "sender_email": self.sender_email,
            }

    def __bytes__(self):
        return FILE_TRANSFER_ACCEPT_REQUEST_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# 5(a). `S -> X -> Y, S -> Y -> X`: if Y accepted, server sends X's IP address to Y and server sends Y's IP address to X
# 5(b). `S -> Deny -> X`: if Y denied, server notifies X of denial

FILE_TRANSFER_EXCHANGE_ADDRESS_PACKETS_NAME = b"FTEA"


class FileTransferExchangeAddressPackets:
    def __init__(self, address: str = None, data=None):
        # If address is empty string, the request was denied
        self.address = address
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.address = self.jdict["address"]
        elif address is not None:
            self.jdict = {
                "address": self.address,
            }

    def __bytes__(self):
        return FILE_TRANSFER_EXCHANGE_ADDRESS_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# Part 2: Transfer Protocol

# 1. `X -> Hash(F)/Chunks(F) -> Y`: X sends the hash of F and the number of chunks in F to Y

FILE_TRANSFER_P2P_FILEINFO_PACKETS_NAME = b"FTPF"


class FileTransferP2PFileInfoPackets:
    def __init__(self, file_info: dict = None, data=None):
        self.file_info = file_info
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.file_info = self.jdict["file_info"]
        elif file_info is not None:
            self.jdict = {
                "file_info": self.file_info,
            }

    def __bytes__(self):
        return FILE_TRANSFER_P2P_FILEINFO_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# 2. `X -> NextChunk(F) -> Y`: X sends next chunk of file to Y

FILE_TRANSFER_P2P_CHUNK_PACKETS_NAME = b"FTPF"


class FileTransferP2PChunkPackets:
    def __init__(self, chunk: bytes = None, data=None):
        self.chunk = chunk
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.chunk = self.jdict["chunk"]
        elif chunk is not None:
            self.jdict = {
                "chunk": self.chunk,
            }

    def __bytes__(self):
        return FILE_TRANSFER_P2P_CHUNK_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# 3. `Y -> Success/Failure -> X`: after all chunks received, Y sends success/failure to X

# Status packets
