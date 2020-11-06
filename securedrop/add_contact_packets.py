import json

ADD_CONTACT_PACKETS_NAME = b"ADDC"


class AddContactPackets:
    def __init__(self, name: str = None, email: str = None, data=None):
        self.name, self.email = name, email
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.name, self.email = self.jdict["name"], self.jdict["email"]
        elif email is not None:
            self.jdict = {
                "name": self.name,
                "email": self.email,
            }

    def __bytes__(self):
        return ADD_CONTACT_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
