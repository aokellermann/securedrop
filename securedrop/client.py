#!/usr/bin/env python3

import json
import getpass
import os

from securedrop.client_server_base import ClientBase
from securedrop.register_packets import REGISTER_PACKETS_NAME, RegisterPackets
from securedrop.status_packets import STATUS_PACKETS_NAME, StatusPackets
from securedrop.login_packets import LOGIN_PACKETS_NAME, LoginPackets
from securedrop.add_contact_packets import ADD_CONTACT_PACKETS_NAME, AddContactPackets
from securedrop.utils import validate_and_normalize_email

DEFAULT_FILENAME = 'client.json'
DEFAULT_HOSTNAME = '127.0.0.1'
DEFAULT_PORT = 6969


class RegisteredUsers:
    def __init__(self, filename):
        self.filename = filename
        self.users = set()
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.users = set(json.load(f))

    def make_json(self):
        return list(self.users)

    def write_json(self):
        with open(self.filename, 'w') as f:
            json.dump(self.make_json(), f)

    def register_prompt(self):
        name = input("Enter Full Name: ")
        email = input("Enter Email Address: ")
        valid_email = validate_and_normalize_email(email)
        if valid_email is None:
            raise RuntimeError("Invalid Email Address.")
        if valid_email in self.users:
            raise RuntimeError("That email already exists!")

        pw1 = getpass.getpass(prompt="Enter Password: ")
        pw2 = getpass.getpass(prompt="Re-enter password: ")
        if pw1 != pw2:
            raise RuntimeError("The two entered passwords don't match!")

        # enforce password length to min of 12 characters
        if len(pw1) < 12:
            raise RuntimeError("Password is too short! Password must be at least 12 characters")

        if not name or not valid_email or not pw1:
            raise RuntimeError("Empty input")

        return name, valid_email, pw1

    def register_user(self, email):
        self.users.add(email)
        self.write_json()
        print("User registered.")

    def login_prompt(self):
        email = input("Enter Email Address: ")
        password = getpass.getpass(prompt="Enter Password: ")
        return email, password


class Client(ClientBase):
    users: RegisteredUsers

    def __init__(self, host: str, prt: int, filename):
        super().__init__(host, prt)
        self.filename = filename
        try:
            self.users = RegisteredUsers(filename)
            self.user = None
        except Exception as e:
            print("Exiting SecureDrop")
            raise e

    async def main(self):
        await super().main()
        try:
            if not self.users.users:
                decision = input(
                    "No users are registered with this client.\nDo you want to register a new user (y/n)? ")
                if str(decision) == 'y':
                    self.user = await self.register()
                    if self.user:
                        await self.sh()
                    else:
                        raise RuntimeError("Registration failed.")
                else:
                    raise RuntimeError("You must register a user before using securedrop")
            else:
                self.user = await self.login()
                if self.user:
                    await self.sh()
                else:
                    raise RuntimeError("Login failed.")
        except Exception as e:
            print("Exiting SecureDrop")
            raise e

    async def register(self):
        msg, email = None, None
        try:
            name, email, pw = self.users.register_prompt()
            await self.write(bytes(RegisterPackets(name, email, pw)))
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)
            self.users.register_user(email)
        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to register: ", msg)
            return None
        return email

    async def login(self):
        msg, email = None, None
        try:
            email, pw = self.users.login_prompt()
            await self.write(bytes(LoginPackets(email, pw)))
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)
        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to login: ", msg)
            return None
        return email

    async def sh(self):
        try:
            print("Welcome to SecureDrop")
            print("Type \"help\" For Commands")
            while True:
                cmd = input("secure_drop> ")
                if cmd == "help":
                    print("\"add\"  \t-> Add a new contact")
                    print("\"list\"  \t-> List all online contacts")
                    print("\"send\"  \t-> Transfer file to contact")
                    print("\"exit\"  \t-> Exit SecureDrop")
                elif cmd == "add":
                    await self.add_contact()
                elif cmd == "list":
                    pass
                elif cmd == "send":
                    pass
                elif cmd == "exit":
                    break

        except Exception as e:
            print("Exiting SecureDrop")
            raise e

    async def add_contact(self):
        msg = None
        try:
            name = input("Enter Full Name: ")
            email = input("Enter Email Address: ")
            valid_email = validate_and_normalize_email(email)
            if valid_email is None:
                raise RuntimeError("Invalid Email Address.")
            if not name:
                raise RuntimeError("Empty name input.")

            await self.write(bytes(AddContactPackets(name, valid_email)))
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)
        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to add contact: ", msg)


def main(hostname=None, port=None, filename=None, verbose=None):
    hostname = hostname if hostname is not None else DEFAULT_HOSTNAME
    port = port if port is not None else DEFAULT_PORT
    filename = filename if filename is not None else DEFAULT_FILENAME
    verbose = verbose if verbose is not None else False
    Client(hostname, port, filename).run()


if __name__ == "__main__":
    main()
