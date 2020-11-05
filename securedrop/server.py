#!/usr/bin/env python3

import selectors
import os
import base64
import hashlib
import json

import securedrop.command as command
import securedrop.register_packets as register_command
import securedrop.status_packets as status_packets
import securedrop.login_packets as login_packets
import securedrop.add_contact_packets as add_contact_packets
import securedrop.utils as utils

sd_filename = 'server.json'
hostname = ''
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
        return None

    def login(self, email, password):
        if email not in self.users:
            print("That user doesn't exist.")
            return "That user doesn't exist."
        if Authentication(key=password, salt=self.users[email].auth.salt) != self.users[email].auth:
            print("Wrong password.")
            return "Wrong password."
        return None

    def add_contact(self, email, contact_name, contact_email):
        if not contact_email or not contact_name:
            return "Invalid email or contact."
        self.users[email].contacts[contact_email] = contact_name
        self.write_json()
        return None


class Server(command.CommandReceiver):
    def __init__(self, host: str, prt: int, filename):
        self.users = RegisteredUsers(filename)
        self.email_to_sock = dict()
        self.sock_to_email = dict()
        super().__init__(host, prt)

    def run(self):
        try:
            super().run()
        finally:
            for sock, email in self.sock_to_email:
                sock.close()

    def on_command_received(self, conversation, sock):
        with conversation.lock:
            msg_type = conversation.inbound_packets.get_type()
            if msg_type is not None:
                if msg_type == register_command.REGISTER_PACKETS_NAME:
                    self.process_register(conversation, sock)
                elif msg_type == login_packets.LOGIN_PACKETS_NAME:
                    self.process_login(conversation, sock)
                elif msg_type == add_contact_packets.ADD_CONTACT_PACKETS_NAME:
                    self.add_contact(conversation, sock)

    def process_register(self, conversation, sock):
        reg = register_command.RegisterPackets(data=conversation.inbound_packets.get_message())
        msg = self.users.register_new_user(reg.name, reg.email, reg.password)
        ok = msg is None
        conversation.outbound_packets = status_packets.StatusPackets(status=ok, message=msg)
        if ok:
            self.email_to_sock[reg.email] = sock
            self.sock_to_email[sock] = reg.email

    def process_login(self, conversation, sock):
        log = login_packets.LoginPackets(data=conversation.inbound_packets.get_message())
        msg = self.users.login(log.email, log.password)
        ok = msg is None
        conversation.outbound_packets = status_packets.StatusPackets(status=ok, message=msg)
        if ok:
            self.email_to_sock[log.email] = sock
            self.sock_to_email[sock] = log.email

    def add_contact(self, conversation, sock):
        addc = add_contact_packets.AddContactPackets(data=conversation.inbound_packets.get_message())
        msg = self.users.add_contact(self.sock_to_email[sock], addc.name, addc.email)
        ok = msg is None
        conversation.outbound_packets = status_packets.StatusPackets(status=ok, message=msg)


server = None


def get_state():
    return server


def main():
    global server
    server = Server(hostname, port, sd_filename)
    try:
        server.run()
    except Exception:
        print("Caught exception. Exiting...")


if __name__ == "__main__":
    main()
