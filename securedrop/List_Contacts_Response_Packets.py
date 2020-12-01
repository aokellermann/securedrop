import json

LIST_CONTACTS_RESPONSE_PACKETS_NAME = b"LCRN"


class ListContactsPacketsResponse:
    def __init__(self, message=None, data=None):
        self.message = message
        self.jdict = dict()
        if data is not None:
            self.jdict = json.loads(data)
            self.message = self.jdict["message"]
        elif message is not None:
            self.jdict = {
                "message": self.message,
            }

    def __bytes__(self):
        return LIST_CONTACTS_RESPONSE_PACKETS_NAME + bytes(json.dumps(self.jdict), encoding='ascii')

