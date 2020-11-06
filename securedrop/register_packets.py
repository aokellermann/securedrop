import json

REGISTER_PACKETS_NAME = b"RGTR"


class RegisterPackets:
    def __init__(self, name: str = None, email: str = None, password: str = None, data=None):
        self.name, self.email, self.password = name, email, password
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.name, self.email, self.password = self.jdict["name"], self.jdict["email"], self.jdict["password"]
        elif name is not None and email is not None and password is not None:
            self.jdict = {
                "name": self.name,
                "email": self.email,
                "password": self.password,
            }

    def __bytes__(self):
        return REGISTER_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
