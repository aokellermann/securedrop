import os
from base64 import b64encode, b64decode
from math import ceil
from multiprocessing import shared_memory

from securedrop import ClientBase, ServerBase
from securedrop.file_transfer_packets import FILE_TRANSFER_P2P_CHUNK_SIZE, FileTransferP2PChunkPackets, \
    FileTransferP2PFileInfoPackets, FILE_TRANSFER_P2P_FILEINFO_PACKETS_NAME, FILE_TRANSFER_P2P_CHUNK_PACKETS_NAME
from securedrop.status_packets import StatusPackets
from securedrop.utils import sha256_file


class P2PClient(ClientBase):
    def __init__(self, port, token, in_filename, in_file_size, in_file_sha256, progress_shm_name, progress_lock):
        super().__init__("localhost", port)
        self.token, self.in_filename, self.in_file_size, self.in_file_sha256, self.progress_shm_name, self.progress_lock = token, in_filename, in_file_size, in_file_sha256, progress_shm_name, progress_lock

    async def main(self):
        await super().main()

        progress = shared_memory.SharedMemory(self.progress_shm_name)
        try:

            total_chunks = ceil(self.in_file_size / FILE_TRANSFER_P2P_CHUNK_SIZE)
            file_info = {
                "name": os.path.basename(self.in_filename),
                "chunks": total_chunks,
                "SHA256": self.in_file_sha256,
            }

            await self.write(bytes(FileTransferP2PFileInfoPackets(file_info, self.token)))

            chunks_sent = 0
            with self.progress_lock:
                progress.buf[0:4] = chunks_sent.to_bytes(4, byteorder='little')
                progress.buf[4:8] = total_chunks.to_bytes(4, byteorder='little')

            with open(self.in_filename, "rb") as file:
                while chunk := b64encode(file.read(FILE_TRANSFER_P2P_CHUNK_SIZE)):
                    await self.write(bytes(FileTransferP2PChunkPackets(chunk)))
                    chunks_sent += 1
                    with self.progress_lock:
                        progress.buf[0:4] = chunks_sent.to_bytes(4, byteorder='little')
        finally:
            progress.close()


class P2PServer(ServerBase):
    def __init__(self, token, out_dir, progress_shm_name, lock, listen_port_shm_name):
        super().__init__()
        self.token = token
        self.out_dir, self.lock = out_dir, lock
        self.received_chunks, self.total_chunks, self.sha256 = 0, 0, ""
        self.progress = shared_memory.SharedMemory(progress_shm_name)
        self.listen_port_shm = shared_memory.SharedMemory(listen_port_shm_name)
        self.sentinel = None
        self.out_filename = ""
        self.verified = False
        self.out_path = ""

    def run(self, port, shm_name):
        self.sentinel = shared_memory.SharedMemory(shm_name)
        self.sentinel.buf[0] = 0
        try:
            self.listen(port)
            with self.lock:
                self.listen_port_shm.buf[0:4] = int(next(iter(self.listen_ports))).to_bytes(4, byteorder='little')

            super().run(port, shm_name)
        finally:
            self.progress.close()
            self.listen_port_shm.close()
            self.sentinel.close()

    async def on_stream_accepted(self, stream, address):
        pass

    async def on_stream_closed(self, stream, address):
        pass

    async def on_data_received(self, data, stream):
        prefix = data[:4]
        data = data[4:]

        if prefix == FILE_TRANSFER_P2P_FILEINFO_PACKETS_NAME:
            await self.process_fileinfo(FileTransferP2PFileInfoPackets(data=data), stream)
        elif not self.verified:
            print("Connection not verified!")
            stream.close()
        elif prefix == FILE_TRANSFER_P2P_CHUNK_PACKETS_NAME:
            await self.process_chunk(FileTransferP2PChunkPackets(data=data))
            if self.received_chunks == self.total_chunks:
                await self.complete_transfer(stream)

    async def process_fileinfo(self, file_info, stream):
        if self.token != file_info.token:
            print("Token doesn't match!")
            stream.close()

        self.verified = True
        self.out_filename = file_info.file_info["name"]
        self.total_chunks = file_info.file_info["chunks"]
        self.sha256 = file_info.file_info["SHA256"]

        with self.lock:
            self.progress.buf[0:4] = self.received_chunks.to_bytes(4, byteorder='little')
            self.progress.buf[4:8] = self.total_chunks.to_bytes(4, byteorder='little')

    async def process_chunk(self, chunk):
        if not self.out_path:
            self.out_path = os.path.join(self.out_dir, self.out_filename)
        with open(self.out_path, "ab") as file:
            file.write(b64decode(chunk.chunk))
            self.received_chunks += 1
            with self.lock:
                self.progress.buf[0:4] = self.received_chunks.to_bytes(4, byteorder='little')

    async def complete_transfer(self, stream):
        compare_sha256 = sha256_file(self.out_path)
        msg = "" if self.sha256 == compare_sha256 else "File hashes don't match!"
        await self.write(stream, bytes(StatusPackets(msg)))
        self.sentinel.buf[0] = 1
