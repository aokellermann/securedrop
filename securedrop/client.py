#!/usr/bin/env python3

import json
import getpass
import os
import selectors

import securedrop.command as command
import securedrop.register_packets as register_packets
import securedrop.status_packets as status_packets
import securedrop.login_packets as login_packets
import securedrop.utils as utils

sd_filename = 'client.json'
hostname = ''
port = 6969


class RegisteredUsers:
    def __init__(self, host: str, prt: int, sock, sel, filename):
        self.host, self.port, self.sock, self.sel, self.filename = host, prt, sock, sel, filename
        self.users = set()
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.users = set(json.load(f))

    def make_json(self):
        return list(self.users)

    def write_json(self):
        with open(self.filename, 'w') as f:
            json.dump(self.make_json(), f)

    def register_new_user(self):
        name = input("Enter Full Name: ")
        email = input("Enter Email Address: ")
        if email in self.users:
            raise RuntimeError("That email already exists!")

        pw1 = getpass.getpass(prompt="Enter Password: ")
        pw2 = getpass.getpass(prompt="Re-enter password: ")
        if pw1 != pw2:
            raise RuntimeError("The two entered passwords don't match!")

        if name and email and pw1 and pw2:
            cmd = command.Command(self.host, self.port, self.sock, self.sel,
                                  selectors.EVENT_READ | selectors.EVENT_WRITE,
                                  packets=register_packets.RegisterPackets(name, email, pw1))
            timer = utils.Timer(5).start()
            resp = [None]
            cmd.run(timer.is_triggered, resp, 0)
            status = status_packets.StatusPackets(data=resp[0])
            if status.ok:
                self.users.add(email)
                self.write_json()
                print("User registered.")
                return email
            else:
                print("Failed to register user: " + str(status.message))
                return None
        else:
            raise RuntimeError("Invalid input")

    def login(self):
        email = input("Enter Email Address: ")
        password = getpass.getpass(prompt="Enter Password: ")
        cmd = command.Command(self.host, self.port, self.sock, self.sel,
                              selectors.EVENT_READ | selectors.EVENT_WRITE,
                              packets=login_packets.LoginPackets(email, password))
        timer = utils.Timer(5).start()
        resp = [None]
        cmd.run(timer.is_triggered, resp, 0)
        status = status_packets.StatusPackets(data=resp[0])
        if status.ok:
            print("User logged in.")
            return email
        else:
            print("Failed to log in: " + str(status.message))
            return None


class Client:
    users: RegisteredUsers

    def __init__(self, host: str, prt: int, sock, sel, filename):
        try:
            self.users = RegisteredUsers(host, prt, sock, sel, filename)
            self.user = None
        except Exception as e:
            print("Exiting SecureDrop")
            raise e

    def run(self):
        try:
            if not self.users.users:
                decision = input(
                    "No users are registered with this client.\nDo you want to register a new user (y/n)? ")
                if str(decision) == 'y':
                    self.user = self.users.register_new_user()
                    if self.user:
                        self.login()
                    else:
                        raise RuntimeError("Registration failed.")
                else:
                    raise RuntimeError("You must register a user before using securedrop")
            else:
                self.user = self.users.login()
                if self.user:
                    self.login()
                else:
                    raise RuntimeError("Login failed.")
        except Exception as e:
            print("Exiting SecureDrop")
            raise e

    def login(self):
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
                    # name = input("Enter Full Name: ")
                    # email = input("Enter Email Address: ")
                    # if name and email:
                    #     user.contacts[email] = name
                    #     self.users.write_json()
                    # else:
                    #     print("Name and email must both be non-empty.")
                    pass
                elif cmd == "list":
                    pass
                elif cmd == "send":
                    pass
                elif cmd == "exit":
                    break

        except Exception as e:
            print("Exiting SecureDrop")
            raise e


def main():
    client_sel = selectors.DefaultSelector()
    client_sock = utils.make_sock()
    try:
        client = Client(hostname, port, client_sock, client_sel, sd_filename)
        client.run()
    finally:
        client_sel.close()
        client_sock.close()


if __name__ == "__main__":
    main()
