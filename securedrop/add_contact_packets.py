import json

import securedrop.command as command

ADD_CONTACT_PACKETS_NAME = b"ADDC"


class AddContactPackets(command.Packets):
    def __init__(self, name: str = None, email: str = None, data=None):
        self.name, self.email = name, email
        jdict = dict()
        if data is not None:
            jdict = json.loads(data)
            self.name, self.email = jdict["name"], jdict["email"]
        elif email is not None:
            jdict = {
                "name": self.name,
                "email": self.email,
            }
        super().__init__(name=ADD_CONTACT_PACKETS_NAME, message=bytes(json.dumps(jdict), encoding='ascii'))
