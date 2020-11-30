import json

LIST_CONTACTS_PACKETS_NAME = b"LCPN"


class ListContactsPackets:
    def __init__(self, name: str = None, data=None):
        self.name = name
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.name = self.jdict["name"]
        elif name is not None:
            self.jdict = {
                "name": self.name
            }

    def __bytes__(self):
        return LIST_CONTACTS_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
