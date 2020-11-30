import json

LIST_CONTACTS_PACKETS_NAME = b"LCPN"


class ListContactsPackets:
    def __init__(self, email: str = None, data=None):
        self.email = email
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.email = self.jdict["email"]
        elif email is not None:
            self.jdict = {
                "email": self.email
            }

    def __bytes__(self):
        return LIST_CONTACTS_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
