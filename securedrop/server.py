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


class Server(command.CommandReceiver):
    def __init__(self, host: str, prt: int, sock, sel, filename):
        self.users = RegisteredUsers(filename)
        self.online_users = set()
        super().__init__(host, prt, sock, sel, selectors.EVENT_READ | selectors.EVENT_WRITE)

    def on_command_received(self, conversation):
        with conversation.lock:
            msg_type = conversation.inbound_packets.get_type()
            if msg_type is not None:
                if msg_type == register_command.REGISTER_PACKETS_NAME:
                    self.process_register(conversation)
                elif msg_type == login_packets.LOGIN_PACKETS_NAME:
                    self.process_login(conversation)

    def process_register(self, conversation):
        reg = register_command.RegisterPackets(data=conversation.inbound_packets.get_message())
        msg = self.users.register_new_user(reg.name, reg.email, reg.password)
        ok = msg is None
        print("ok: ", ok, " msg: ", msg)
        conversation.outbound_packets = status_packets.StatusPackets(status=ok, message=msg)
        if ok:
            self.online_users.add(reg.email)

    def process_login(self, conversation):
        log = login_packets.LoginPackets(data=conversation.inbound_packets.get_message())
        msg = self.users.login(log.email, log.password)
        ok = msg is None
        print("ok: ", ok, " msg: ", msg)
        conversation.outbound_packets = status_packets.StatusPackets(status=ok, message=msg)
        if ok:
            self.online_users.add(log.email)


def main():
    server_sel = selectors.DefaultSelector()
    server_sock = utils.make_sock()
    recv = Server(hostname, port, server_sock, server_sel, sd_filename)
    try:
        recv.run(lambda: False)
    except Exception:
        print("Caught exception. Exiting...")
    finally:
        server_sel.close()
        server_sock.close()


if __name__ == "__main__":
    main()
