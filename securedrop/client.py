import json
import getpass
import os
import hashlib
import base64

from Crypto import Random
from Crypto.Cipher import AES


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


class AESWrapper(object):

    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        verify = hashlib.sha256((raw.encode())).hexdigest()
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        bites = base64.b64encode(iv + cipher.encrypt(raw.encode()))
        return dict({"data": bites.decode('ascii'), "verify": verify})

    def decrypt(self, enc):
        data = enc["data"]
        verify = enc["verify"]
        data = base64.b64decode(data)
        iv = data[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        result = self._unpad(cipher.decrypt(data[AES.block_size:])).decode('utf-8')
        if verify == hashlib.sha256((result.encode())).hexdigest():
            return result
        else:
            raise RuntimeError("Decryption was not successful, could not verify input")

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]


class ClientData:
    name: str
    email: str
    contacts: dict
    auth: Authentication
    email_hash: str
    enc_name: dict
    enc_contacts: dict

    def __init__(self, nm=None, em=None, cs=None, password=None, jdict=None):
        if jdict is not None:
            self.enc_name, self.email_hash, self.enc_contacts, self.auth = \
                jdict["name"], jdict["email"], jdict["contacts"], Authentication(jdict=jdict["auth"])
        else:
            self.name, self.email, self.contacts, self.auth = nm, em, cs, Authentication(password)
            self.email_hash = hashlib.sha256((self.email.encode())).hexdigest()
            self.encrypt_name_contacts()

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

    def register_new_user(self):
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
            email_hash = hashlib.sha256((email.encode())).hexdigest()
            self.users[email_hash] = ClientData(name, email, {}, pw1)
            self.write_json()
            print("User Registered.")
            return self.users[email_hash]
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
                    user = self.users.register_new_user()
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
                email_hash = hashlib.sha256((email.encode())).hexdigest()
                if email_hash not in self.users.users:
                    raise RuntimeError("That email address is not registered")

                user = self.users.users[email_hash]
                auth = Authentication(str(pw), user.auth.salt)
                if auth != self.users.users[email_hash].auth:
                    raise RuntimeError("Email and Password Combination Invalid.")
                user.email = email
                user.decrypt_name_contacts()
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
