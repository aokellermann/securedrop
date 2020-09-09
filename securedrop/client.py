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
    name: str
    email: str
    contacts: list
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

    def __init__(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                jdict = json.load(f)
                for email, cd in jdict.items():
                    self.users[email] = ClientData(jdict=cd)
        else:
            decision = input("No users are registered with this client.\nDo you want to register a new user (y/n)?")
            if str(decision) == 'y':
                self.register_new_user()
            else:
                raise RuntimeError("You must register a user before using securedrop")

    def make_dict(self):
        return {email: data.make_dict() for email, data in self.users.items()}

    def write_json(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.make_dict(), f)

    def register_new_user(self):
        name = input("Enter Full Name: ")
        email = input("Enter Email Address: ")
        if email in self.users:
            raise RuntimeError("That email already exists!")

        pw1 = getpass.getpass(prompt="Enter Password: ")
        pw2 = getpass.getpass(prompt="Enter Password Again: ")
        if name and email and pw1 and pw2:
            salt = make_salt()
            auth1 = Authentication(str(pw1), salt)
            auth2 = Authentication(str(pw2), salt)
            if auth1 != auth2:
                raise RuntimeError("The two entered passwords don't match!")

            self.users[email] = ClientData(name, email, [], pw1)
        else:
            raise RuntimeError("Invalid input")


class Client:
    users: RegisteredUsers

    def __init__(self, filename):
        self.users = RegisteredUsers(filename)
        self.users.write_json(filename)
