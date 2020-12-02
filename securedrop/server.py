#!/usr/bin/env python3

import os
import base64
import hashlib
import json
from multiprocessing import shared_memory

from email_validator import validate_email, EmailNotValidError

from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
import Crypto.Util.Padding

from securedrop import ServerBase
from securedrop.register_packets import REGISTER_PACKETS_NAME, RegisterPackets
from securedrop.status_packets import STATUS_PACKETS_NAME, StatusPackets
from securedrop.login_packets import LOGIN_PACKETS_NAME, LoginPackets
from securedrop.add_contact_packets import ADD_CONTACT_PACKETS_NAME, AddContactPackets

DEFAULT_filename = 'server.json'
DEFAULT_PORT = 6969


def make_salt():
    return get_random_bytes(32)


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
            "salt": base64.b64encode(self.salt).decode('utf-8'),
            "key": base64.b64encode(self.key).decode('utf-8')
        }


class AESWrapper(object):
    def __init__(self, key):
        self.bs = AES.block_size
        self.key = Crypto.Util.Padding.pad(key.encode('utf-8'), self.bs)

    def encrypt(self, raw):
        raw = Crypto.Util.Padding.pad(raw.encode('utf-8'), self.bs)
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        bytes_ = base64.b64encode(iv + cipher.encrypt(raw))
        return bytes_.decode('utf-8')

    def decrypt(self, enc):
        try:
            data = base64.b64decode(enc)
            iv = data[:AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            result = Crypto.Util.Padding.unpad(cipher.decrypt(data[AES.block_size:]), self.bs).decode('utf-8')
            return result
        except ValueError or KeyError:
            raise RuntimeError("Decryption was not successful, could not verify input")


class ClientData:
    name: str
    email: str
    contacts: dict
    auth: Authentication
    email_hash: str
    enc_name: str
    enc_contacts: str

    def __init__(self, name=None, email=None, contacts=None, password=None, jdict=None):
        if jdict is not None:
            self.enc_name, self.email_hash, self.enc_contacts, self.auth = \
                jdict["name"], jdict["email"], jdict["contacts"], Authentication(jdict=jdict["auth"])
        else:
            self.name, self.email, self.contacts, self.auth = name, email, contacts, Authentication(password)
            self.email_hash = hashlib.sha256((self.email.encode())).hexdigest()

    def __eq__(self, other):
        return self.name == other.name

    def make_dict(self):
        self.email_hash = hashlib.sha256((self.email.encode())).hexdigest()
        self.encrypt_name_contacts()
        return {
            "name": self.enc_name,
            "email": self.email_hash,
            "contacts": self.enc_contacts,
            "auth": self.auth.make_dict()
        }

    def encrypt_name_contacts(self):
        if self.email is None:
            raise RuntimeError("Encrypt: A email/key must be provided")
        enc = AESWrapper(self.email)
        self.enc_name = enc.encrypt(self.name)
        dump = json.dumps(self.contacts)
        self.enc_contacts = enc.encrypt(dump)

    def decrypt_name_contacts(self):
        if self.email is None:
            raise RuntimeError("Decrypt: A email/key must be provided")
        enc = AESWrapper(self.email)
        self.name = enc.decrypt(self.enc_name)
        self.contacts = json.loads(enc.decrypt(self.enc_contacts))


def validate_and_normalize_email(email):
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError as e:
        print(str(e))


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
        valid_email = validate_and_normalize_email(email)
        if valid_email is None:
            return "Invalid Email Address."
        email_hash = hashlib.sha256((valid_email.encode())).hexdigest()
        if email_hash in self.users:
            return "User already exists."
        self.users[email_hash] = ClientData(name=name, email=valid_email, password=password, contacts=dict())
        self.write_json()
        print("User Registered.")
        return ""

    def login(self, email, password):
        email_hash = hashlib.sha256((email.encode())).hexdigest()
        if email_hash not in self.users:
            print("Email and Password Combination Invalid.")
            return "Email and Password Combination Invalid."

        user = self.users[email_hash]
        auth = Authentication(str(password), user.auth.salt)
        if auth != self.users[email_hash].auth:
            print("Email and Password Combination Invalid.")
            return "Email and Password Combination Invalid."

        user.email = email
        user.decrypt_name_contacts()
        return ""

    def add_contact(self, email, contact_name, contact_email):
        valid_email = validate_and_normalize_email(email)
        if valid_email is None:
            return "Invalid Email Address."
        if not contact_name:
            return "Invalid contact name."

        email_hash = hashlib.sha256((email.encode())).hexdigest()
        user = self.users[email_hash]
        if not user.contacts:
            user.contacts = dict()
        user.contacts[contact_email] = contact_name
        self.write_json()
        return ""


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
    def __init__(self, port=None, filename=None):
        port = port if port is not None else DEFAULT_PORT
        filename = filename if filename is not None else DEFAULT_filename
        self.port, self.filename = port, filename
        self.sentinel = shared_memory.SharedMemory(create=True, size=1)
        self.sentinel.buf[0] = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def sentinel_name(self):
        return self.sentinel.name

    def run(self):
        try:
            server = Server(self.filename)
            server.run(self.port, self.sentinel_name())
        except Exception:
            print("Caught exception. Exiting...")
        finally:
            self.sentinel.buf[0] = 1

    def close(self):
        self.sentinel.close()
        self.sentinel.unlink()


def main(port=None, filename=None):
    port = port if port is not None else DEFAULT_PORT
    filename = filename if filename is not None else DEFAULT_filename
    with ServerDriver(port, filename) as driver:
        driver.run()


if __name__ == "__main__":
    main()
