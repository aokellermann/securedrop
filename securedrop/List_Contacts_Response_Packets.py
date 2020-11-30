import json

LIST_CONTACTS_RESPONSE_PACKETS_NAME = b"LCPRN"


class ListContactsPacketsResponse:
    def __init__(self, name: str = None, email: str = None, data=None):
        self.name, self.email = name, email
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.name = self.jdict["name"]
            self.email = self.jdict["email"]
        elif name is not None:
            self.jdict = {
                "name": self.name,
                "email": self.email
            }

    def __bytes__(self):
        return LIST_CONTACTS_RESPONSE_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
