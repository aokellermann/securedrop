import json
import getpass
import os
import hashlib
import base64


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

    def __init__(self, nm=None, em=None, cs=None, password=None, jdict=None):
        if jdict is not None:
            self.name, self.email, self.contacts, self.auth = \
                jdict["name"], jdict["email"], jdict["contacts"], Authentication(jdict=jdict["auth"])
        else:
            self.name, self.email, self.contacts, self.auth = nm, em, cs, Authentication(password)

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

    def register_new_user(self, filename):
        name = input("Enter Full Name: ")
        email = input("Enter Email Address: ")
        if email in self.users:
            raise RuntimeError("That email already exists!")

        pw1 = getpass.getpass(prompt="Enter Password: ")
        pw2 = getpass.getpass(prompt="Re-enter password: ")
        if name and email and pw1 and pw2:
            salt = make_salt()
            auth1 = Authentication(str(pw1), salt)
            auth2 = Authentication(str(pw2), salt)
            if auth1 != auth2:
                raise RuntimeError("The two entered passwords don't match!")

            print("Passwords Match.")
            self.users[email] = ClientData(name, email, {}, pw1)
            self.write_json()
            print("User Registered.")
            return self.users[email]
        else:
            raise RuntimeError("Invalid input")


class Client:
    users: RegisteredUsers

    def __init__(self, filename):
        try:
            self.users = RegisteredUsers(filename)
            if not self.users.users:
                decision = input(
                    "No users are registered with this client.\nDo you want to register a new user (y/n)? ")
                if str(decision) == 'y':
                    user = self.users.register_new_user(filename)
                    self.login(user)
                else:
                    raise RuntimeError("You must register a user before using securedrop")

        except Exception as e:
            print("Exiting SecureDrop")
            raise e

    def login(self, user=None):
        try:
            if not user:
                email = input("Enter Email Address: ")
                pw = getpass.getpass(prompt="Enter Password: ")

                if email not in self.users.users:
                    raise RuntimeError("That email address is not registered")

                user = self.users.users[email]
                auth = Authentication(str(pw), user.auth.salt)
                if auth != self.users.users[email].auth:
                    raise RuntimeError("Email and Password Combination Invalid.")

            print("Welcome to SecureDrop")
            print("Type \"help\" For Commands")

            while True:
                command = input("secure_drop> ")
                if command == "help":
                    print("\"add\"  \t-> Add a new contact")
                    print("\"list\"  \t-> List all online contacts")
                    print("\"send\"  \t-> Transfer file to contact")
                    print("\"exit\"  \t-> Exit SecureDrop")
                elif command == "add":
                    name = input("Enter Full Name: ")
                    email = input("Enter Email Address: ")
                    if name and email:
                        user.contacts[email] = name
                        self.users.write_json()
                    else:
                        print("Name and email must both be non-empty.")
                    pass
                elif command == "list":
                    pass
                elif command == "send":
                    pass
                elif command == "exit":
                    break

        except Exception as e:
            print("Exiting SecureDrop")
            raise e
        else:
            print("Exiting SecureDrop")
