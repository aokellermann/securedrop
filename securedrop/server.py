#!/usr/bin/env python3

import os
import base64
import hashlib
import json
from multiprocessing import shared_memory

from securedrop import ServerBase
from securedrop.register_packets import REGISTER_PACKETS_NAME, RegisterPackets
from securedrop.status_packets import STATUS_PACKETS_NAME, StatusPackets
from securedrop.login_packets import LOGIN_PACKETS_NAME, LoginPackets
from securedrop.add_contact_packets import ADD_CONTACT_PACKETS_NAME, AddContactPackets

sd_filename = 'server.json'
port = 6969


def make_salt():
    return os.urandom(32)


class Authentication:
    salt: bytes
    key: bytes

    def __init__(self, key=None, salt=None, jdict=None):
        if key is None and jdict is None:
            raise RuntimeError("Either a key or a jdict must be provided")

        if salt is None:
            salt = os.urandom(32)

        if jdict is not None:
            salt, key = base64.b64decode(jdict["salt"]), base64.b64decode(jdict["key"])
        elif key is not None:
            key = hashlib.pbkdf2_hmac('sha512', key.encode('utf-8'), salt, 10000)

        self.salt, self.key = salt, key

    def __eq__(self, other):
        return self.salt == other.salt and self.key == other.key

    def make_dict(self):
        return {
            "salt": base64.b64encode(self.salt).decode('ascii'),
            "key": base64.b64encode(self.key).decode('ascii')
        }


class ClientData:
    # todo: encrypt name and contacts
    name: str
    email: str
    contacts: dict
    auth: Authentication

    def __init__(self, name=None, email=None, contacts=None, password=None, jdict=None):
        if jdict is not None:
            self.name, self.email, self.contacts, self.auth = \
                jdict["name"], jdict["email"], jdict["contacts"], Authentication(jdict=jdict["auth"])
        else:
            self.name, self.email, self.contacts, self.auth = name, email, contacts, Authentication(password)
        if self.contacts is None:
            self.contacts = dict()

    def __eq__(self, other):
        return self.name == other.name

    def make_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "contacts": self.contacts,
            "auth": self.auth.make_dict()
        }


class RegisteredUsers:
    users = dict()
    filename: str

    def __init__(self, filename):
        self.filename = filename
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                jdict = json.load(f)
                for email, cd in jdict.items():
                    self.users[email] = ClientData(jdict=cd)

    def make_dict(self):
        return {email: data.make_dict() for email, data in self.users.items()}

    def write_json(self):
        with open(self.filename, 'w') as f:
            json.dump(self.make_dict(), f)

    def register_new_user(self, name, email, password):
        if email in self.users:
            return "User already exists."
        self.users[email] = ClientData(name=name, email=email, password=password)
        self.write_json()
        print("User Registered.")
        return ""

    def login(self, email, password):
        if email not in self.users:
            print("That user doesn't exist.")
            return "That user doesn't exist."
        if Authentication(key=password, salt=self.users[email].auth.salt) != self.users[email].auth:
            print("Wrong password.")
            return "Wrong password."
        return ""

    def add_contact(self, email, contact_name, contact_email):
        if not contact_email or not contact_name:
            return "Invalid email or contact."
        self.users[email].contacts[contact_email] = contact_name
        self.write_json()
        return None


class Server(ServerBase):
    def __init__(self, filename):
        self.users = RegisteredUsers(filename)
        self.email_to_sock = dict()
        self.sock_to_email = dict()
        super().__init__()

    async def on_data_received(self, data, stream):
        if len(data) < 4:
            print("Server sent invalid data")
            return

        prefix = data[:4]
        data = data[4:]
        if prefix == REGISTER_PACKETS_NAME:
            await self.process_register(RegisterPackets(data=data), stream)
        elif prefix == LOGIN_PACKETS_NAME:
            await self.process_login(LoginPackets(data=data), stream)
        elif prefix == ADD_CONTACT_PACKETS_NAME:
            await self.add_contact(AddContactPackets(data=data), stream)

    async def write_status(self, stream, msg):
        await self.write(stream, bytes(StatusPackets(msg)))

    async def process_register(self, reg, stream):
        msg = self.users.register_new_user(reg.name, reg.email, reg.password)
        if msg == "":
            self.email_to_sock[reg.email] = stream
            self.sock_to_email[stream] = reg.email
        await self.write_status(stream, msg)

    async def process_login(self, log, stream):
        msg = self.users.login(log.email, log.password)
        if msg == "":
            self.email_to_sock[log.email] = stream
            self.sock_to_email[stream] = log.email
        await self.write_status(stream, msg)

    async def add_contact(self, addc, stream):
        msg = self.users.add_contact(self.sock_to_email[stream], addc.name, addc.email)
        await self.write_status(stream, msg)


class ServerDriver:
    def __init__(self):
        self.shm = shared_memory.SharedMemory(create=True, size=1)
        self.shm.buf[0] = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def shm_name(self):
        return self.shm.name

    def run(self):
        try:
            server = Server(sd_filename)
            server.run(port, self.shm_name())
        except Exception:
            print("Caught exception. Exiting...")
        finally:
            self.shm.buf[0] = 1

    def close(self):
        self.shm.close()
        self.shm.unlink()


if __name__ == "__main__":
    with ServerDriver() as driver:
        driver.run()
