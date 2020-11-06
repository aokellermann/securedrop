import json

LOGIN_PACKETS_NAME = b"LGIN"


class LoginPackets:
    def __init__(self, email: str = None, password: str = None, data=None):
        self.email, self.password = email, password
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.email, self.password = self.jdict["email"], self.jdict["password"]
        elif email is not None and password is not None:
            self.jdict = {
                "email": self.email,
                "password": self.password,
            }

    def __bytes__(self):
        return LOGIN_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
