import json

LIST_CONTACTS_PACKETS_NAME = b"LCPN"


class ListContactsPackets:
    def __init__(self, data=None):
        self.jdict = dict()

    def __bytes__(self):
        return LIST_CONTACTS_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
