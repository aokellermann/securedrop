#!/usr/bin/env python3

import json
import getpass
import os
import hashlib

from securedrop.client_server_base import ClientBase
from securedrop.register_packets import REGISTER_PACKETS_NAME, RegisterPackets
from securedrop.status_packets import STATUS_PACKETS_NAME, StatusPackets
from securedrop.login_packets import LOGIN_PACKETS_NAME, LoginPackets
from securedrop.add_contact_packets import ADD_CONTACT_PACKETS_NAME, AddContactPackets
from securedrop.List_Contacts_Packets import LIST_CONTACTS_PACKETS_NAME, ListContactsPackets
from securedrop.List_Contacts_Response_Packets import LIST_CONTACTS_RESPONSE_PACKETS_NAME, ListContactsPacketsResponse

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
        if email in self.users:
            raise RuntimeError("That email already exists!")

        pw1 = getpass.getpass(prompt="Enter Password: ")
        pw2 = getpass.getpass(prompt="Re-enter password: ")
        if pw1 != pw2:
            raise RuntimeError("The two entered passwords don't match!")

        if not name or not email or not pw1:
            raise RuntimeError("Empty input")

        return name, email, pw1

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
                    await self.list_contacts()
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
            if not name or not email:
                raise RuntimeError("Empty input.")

            await self.write(bytes(AddContactPackets(name, email)))
            msg = StatusPackets(data=(await self.read())[4:]).message
            if msg != "":
                raise RuntimeError(msg)
        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to add contact: ", msg)

    async def list_contacts(self):
        msg = ""
        try:
            with open(sd_filename, 'r') as f:
                jdict = json.load(f)
                email = jdict[0]

                await self.write(bytes(ListContactsPackets(email)))
                contact_dict = ListContactsPacketsResponse(data=(await self.read())[4:]).contacts

                print("Contacts dictionary: ",  contact_dict)

        except RuntimeError as e:
            msg = str(e)
        if msg != "":
            print("Failed to list contacts: ", msg)


def main(hostname=None, port=None, filename=None):
    hostname = hostname if hostname is not None else DEFAULT_HOSTNAME
    port = port if port is not None else DEFAULT_PORT
    filename = filename if filename is not None else DEFAULT_FILENAME
    Client(hostname, port, filename).run()


if __name__ == "__main__":
    main()
