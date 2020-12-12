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
# 5(a). `S -> Token -> Y`: if Y accepted, server sends a unique token Y
# 5(b). `S -> EmptyToken -> X`: if Y denied, server notifies X of denial (empty token)
# 6. `Y -> Port -> S`: Y binds to 0 (OS chooses) and sends the port it's listening on to S
# 7. `S -> Token/Port -> X`: S sends the same token and port to X

# Part 2: Transfer Protocol

# 1. `X -> Hash(F)/Chunks(F)/UniqueToken -> Y`: X sends the hash of F, the number of chunks in F, and a rand token to Y
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
                "file_info": self.file_info,
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


# 5(a). `S -> Token -> Y`: if Y accepted, server sends a unique token Y
# 5(b). `S -> EmptyToken -> X`: if Y denied, server notifies X of denial (empty token)

FILE_TRANSFER_SEND_TOKEN_PACKETS_NAME = b"FTEA"


class FileTransferSendTokenPackets:
    def __init__(self, token: bytes = None, data=None):
        # If token is empty, the request was denied
        self.token = token
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.token = self.jdict["token"]
        elif token is not None:
            self.jdict = {
                "token": self.token,
            }

    def __bytes__(self):
        return FILE_TRANSFER_SEND_TOKEN_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# 6. `Y -> Port -> S`: Y binds to 0 (OS chooses) and sends the port it's listening on to S

FILE_TRANSFER_SEND_PORT_PACKETS_NAME = b"FTSP"


class FileTransferSendPortPackets:
    def __init__(self, port: int = None, data=None):
        # If port is empty, the request was denied
        self.port = port
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.port = self.jdict["port"]
        elif port is not None:
            self.jdict = {
                "port": self.port,
            }

    def __bytes__(self):
        return FILE_TRANSFER_SEND_TOKEN_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# 7. `S -> Token/Port -> X`: S sends the same token and port to X

FILE_TRANSFER_SEND_PORT_TOKEN_PACKETS_NAME = b"FTPT"


class FileTransferSendPortTokenPackets:
    def __init__(self, port: int = None, token: bytes = None, data=None):
        # If port is empty, the request was denied
        self.port, self.token = port, token
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.port, self.token = self.jdict["port"], self.jdict["token"]
        elif port is not None and token is not None:
            self.jdict = {
                "port": self.port,
                "token": self.token,
            }

    def __bytes__(self):
        return FILE_TRANSFER_SEND_TOKEN_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')


# Part 2: Transfer Protocol

# 1. `X -> Hash(F)/Chunks(F)/UniqueToken -> Y`: X sends the hash of F and the number of chunks in F to Y

FILE_TRANSFER_P2P_CHUNK_SIZE = 256 * 16
FILE_TRANSFER_P2P_FILEINFO_PACKETS_NAME = b"FTPF"


class FileTransferP2PFileInfoPackets:
    def __init__(self, file_info: dict = None, token: bytes = None, data=None):
        self.file_info, self.token = file_info, token
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.file_info, self.token = token = self.jdict["file_info"], self.jdict["token"]
        elif file_info is not None and token is not None:
            self.jdict = {
                "file_info": self.file_info,
                "token": self.token,
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
