import json

LIST_CONTACTS_RESPONSE_PACKETS_NAME = b"LCPRN"


class ListContactsPacketsResponse:
    def __init__(self, contacts=None, data=None):
        self.contacts = contacts
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.message = self.jdict["contacts"]
        elif contacts is not None:
            self.jdict = {
                "contacts": self.message,
            }

    def __bytes__(self):
        return LIST_CONTACTS_RESPONSE_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')
