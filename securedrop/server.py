#!/usr/bin/env python3

import os
import base64
import json
from multiprocessing import shared_memory

from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Hash import SHAKE256, SHA256, SHA512
from Crypto.Protocol.KDF import PBKDF2
import Crypto.Util.Padding
from logging import getLogger

from securedrop import ServerBase
from securedrop.register_packets import REGISTER_PACKETS_NAME, RegisterPackets
from securedrop.status_packets import STATUS_PACKETS_NAME, StatusPackets
from securedrop.login_packets import LOGIN_PACKETS_NAME, LoginPackets
from securedrop.add_contact_packets import ADD_CONTACT_PACKETS_NAME, AddContactPackets
from securedrop.file_transfer_packets import FILE_TRANSFER_REQUEST_TRANSFER_PACKETS_NAME, FileTransferRequestPackets, \
    FILE_TRANSFER_CHECK_REQUESTS_PACKETS_NAME, FILE_TRANSFER_CHECK_REQUESTS_RESPONSE_PACKETS_NAME, \
    FileTransferCheckRequestsPackets, FILE_TRANSFER_ACCEPT_REQUEST_PACKETS_NAME, FileTransferAcceptRequestPackets, \
    FileTransferSendTokenPackets, FILE_TRANSFER_SEND_PORT_PACKETS_NAME, FileTransferSendPortPackets, \
    FileTransferSendPortTokenPackets
from securedrop.List_Contacts_Packets import LIST_CONTACTS_PACKETS_NAME, ListContactsPackets
from securedrop.List_Contacts_Response_Packets import LIST_CONTACTS_RESPONSE_PACKETS_NAME, ListContactsResponsePackets
from securedrop.utils import validate_and_normalize_email

DEFAULT_filename = 'server.json'
DEFAULT_PORT = 6969

log = getLogger()


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
            key = PBKDF2(key.encode('utf-8'), salt, 64, count=10000, hmac_hash_module=SHA512)

        self.salt, self.key = salt, key

    def __eq__(self, other):
        return self.salt == other.salt and self.key == other.key

    def make_dict(self):
        return {"salt": base64.b64encode(self.salt).decode('utf-8'), "key": base64.b64encode(self.key).decode('utf-8')}


class AESWrapper(object):
    def __init__(self, key):
        self.bs = AES.block_size
        shake = SHAKE256.new(key.encode('utf-8'))
        self.key = shake.read(32)

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
            self.email_hash = SHA256.new(self.email.encode()).hexdigest()

    def __eq__(self, other):
        return self.name == other.name

    def make_dict(self):
        self.email_hash = SHA256.new(self.email.encode()).hexdigest()
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
        email_hash = SHA256.new(valid_email.encode()).hexdigest()
        if email_hash in self.users:
            return "User already exists."
        self.users[email_hash] = ClientData(name=name, email=valid_email, password=password, contacts=dict())
        self.write_json()
        log.info("User Registered.")
        return ""

    def login(self, email, password):
        email_hash = SHA256.new(email.encode()).hexdigest()
        if email_hash not in self.users:
            log.info("Email and Password Combination Invalid.")
            return "Email and Password Combination Invalid."

        user = self.users[email_hash]
        auth = Authentication(str(password), user.auth.salt)
        if auth != self.users[email_hash].auth:
            log.info("Email and Password Combination Invalid.")
            return "Email and Password Combination Invalid."

        user.email = email
        user.decrypt_name_contacts()
        return ""

    def add_contact(self, email, contact_name, contact_email):
        valid_contact_email = validate_and_normalize_email(contact_email)
        if not valid_contact_email:
            return "Invalid Email Address."
        if not contact_name:
            return "Invalid contact name."
        email_hash = SHA256.new(email.encode()).hexdigest()
        user = self.users[email_hash]
        if not user.contacts:
            user.contacts = dict()
        user.contacts[valid_contact_email] = contact_name
        self.write_json()
        return ""

    def contacts_contains(self, user1_email, user2_email):
        valid_contact_email1 = validate_and_normalize_email(user1_email)
        valid_contact_email2 = validate_and_normalize_email(user2_email)
        if not valid_contact_email1 or not valid_contact_email2:
            return "Invalid Email Address."

        email1_hash = SHA256.new(valid_contact_email1.encode()).hexdigest()
        user = self.users[email1_hash]
        return user.contacts and valid_contact_email2 in user.contacts

    def get_contacts(self, email):
        if not email:
            return "Invalid email address"
        email_hash = SHA256.new(email.encode()).hexdigest()
        return self.users[email_hash].contacts if email_hash in self.users else dict()


class Server(ServerBase):
    def __init__(self, filename):
        self.users = RegisteredUsers(filename)
        self.email_to_sock = dict()
        self.sock_to_email = dict()
        self.sock_to_address = dict()
        self.file_transfer_requests = dict()
        self.file_transfer_recipients = dict()
        super().__init__()

    async def on_data_received(self, data, stream):
        if len(data) < 4:
            log.error("Server sent invalid data")
            return

        prefix = data[:4]
        data = data[4:]
        if prefix == REGISTER_PACKETS_NAME:
            await self.process_register(RegisterPackets(data=data), stream)
        elif prefix == LOGIN_PACKETS_NAME:
            await self.process_login(LoginPackets(data=data), stream)
        elif prefix == ADD_CONTACT_PACKETS_NAME:
            await self.add_contact(AddContactPackets(data=data), stream)
        elif prefix == LIST_CONTACTS_PACKETS_NAME:
            await self.list_contacts(stream)
        elif prefix == FILE_TRANSFER_REQUEST_TRANSFER_PACKETS_NAME:
            await self.process_file_transfer_request(FileTransferRequestPackets(data=data), stream)
        elif prefix == FILE_TRANSFER_CHECK_REQUESTS_PACKETS_NAME:
            await self.send_active_file_transfer_requests(stream)
        elif prefix == FILE_TRANSFER_ACCEPT_REQUEST_PACKETS_NAME:
            await self.process_file_transfer_request_accept(FileTransferAcceptRequestPackets(data=data), stream)
        elif prefix == FILE_TRANSFER_SEND_PORT_PACKETS_NAME:
            await self.process_file_transfer_received_port(FileTransferSendPortPackets(data=data), stream)

    async def on_stream_accepted(self, stream, address):
        self.sock_to_address[stream] = address

    async def on_stream_closed(self, stream, address):
        if stream not in self.sock_to_email:
            return
        email = self.sock_to_email[stream]
        del self.sock_to_email[stream]
        del self.email_to_sock[email]
        del self.sock_to_address[stream]
        log.info("removed {} from online connections".format(email))

    async def write_status(self, stream, msg):
        await self.write(stream, bytes(StatusPackets(msg)))

    async def write_list_contacts_response(self, stream, contacts_dict):
        await self.write(stream, bytes(ListContactsResponsePackets(contacts_dict)))

    async def process_register(self, reg, stream):
        msg = self.users.register_new_user(reg.name, reg.email, reg.password)
        if msg == "":
            self.email_to_sock[reg.email] = stream
            self.sock_to_email[stream] = reg.email
            log.info("added {} to online connections".format(reg.email))
        await self.write_status(stream, msg)

    async def process_login(self, login, stream):
        msg = self.users.login(login.email, login.password)
        if msg == "":
            self.email_to_sock[login.email] = stream
            self.sock_to_email[stream] = login.email
            log.info("added {} to online connectionds".format(login.email))
        await self.write_status(stream, msg)

    async def add_contact(self, addc, stream):
        msg = self.users.add_contact(self.sock_to_email[stream], addc.name, addc.email)
        await self.write_status(stream, msg)

    async def list_contacts(self, stream):
        # three verification steps
        current_user_email = self.sock_to_email[stream]
        # 1: contacts_dict contains the names and email adresses that a user has added
        contacts_dict = self.users.get_contacts(current_user_email)
        contacts_dict_send = dict()

        for email, name in contacts_dict.items():
            # 2: check if a user's contacts have also added the current user as a contact.
            # 3: check if the user is online.
            if email in self.email_to_sock and current_user_email in self.users.get_contacts(email):
                contacts_dict_send[email] = name

        await self.write_list_contacts_response(stream, contacts_dict_send)

    # 1. `X -> Y/F -> S`: X wants to send F to Y
    async def process_file_transfer_request(self, ftrp, stream):
        sender_email = self.sock_to_email[stream]
        recipient_email = ftrp.recipient_email
        msg = ""
        if recipient_email not in self.email_to_sock:
            msg = "User [{}] is not online".format(recipient_email)
        elif not self.users.contacts_contains(recipient_email, sender_email):
            msg = "User [{}] has not added you as a contact".format(recipient_email)
        elif self.sock_to_address[stream][0] != self.sock_to_address[self.email_to_sock[recipient_email]][0]:
            msg = "User [{}] is not on the same network [{}] as you".format(recipient_email,
                                                                            self.sock_to_address[stream][0])
        else:
            if recipient_email not in self.file_transfer_requests:
                self.file_transfer_requests[recipient_email] = dict()
            self.file_transfer_requests[recipient_email][self.sock_to_email[stream]] = ftrp.file_info
        await self.write_status(stream, msg)

    # 2. `Y -> S`: every one second, Y asks server for any requests
    # 3. `S -> X/F -> Y`: server responds with active requests
    async def send_active_file_transfer_requests(self, stream):
        email = self.sock_to_email[stream]
        requests = self.file_transfer_requests[email] if email in self.file_transfer_requests else dict()
        await self.write(stream, bytes(FileTransferCheckRequestsPackets(requests)))

    # 5. `S -> Token -> Y`: if Y accepted, server sends a unique token Y
    # 7. `S -> Token/Port -> X`: S sends the same token and port to X
    async def process_file_transfer_request_accept(self, ftar, stream):
        deny = not ftar.sender_email
        token = get_random_bytes(32) if not deny else b""
        if deny:
            for sender_email in self.file_transfer_requests[self.sock_to_email[stream]].keys():
                await self.write(self.email_to_sock[sender_email], bytes(FileTransferSendPortTokenPackets(0, token)))
            del self.file_transfer_requests[self.sock_to_email[stream]]
        else:
            del self.file_transfer_requests[self.sock_to_email[stream]][ftar.sender_email]
            sender_sock = self.email_to_sock[ftar.sender_email]
            self.file_transfer_recipients[stream] = {"token": token, "sender": sender_sock}
            await self.write(stream, bytes(FileTransferSendTokenPackets(token)))

    # 6. `Y -> Port -> S`: Y binds to 0 (OS chooses) and sends the port it's listening on to S
    # 7. `S -> Token/Port -> X`: S sends the same token and port to X
    async def process_file_transfer_received_port(self, ftsp, stream):
        recipient = self.file_transfer_recipients[stream]
        await self.write(recipient["sender"], bytes(FileTransferSendPortTokenPackets(ftsp.port, recipient["token"])))


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
        except KeyboardInterrupt:
            log.info("Caught KeyboardInterrupt. Exiting.")
        except:
            log.error("Caught exception. Exiting.")
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
