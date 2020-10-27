import socket
import time


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
