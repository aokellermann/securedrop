import json

import securedrop.command as command

REGISTER_PACKETS_NAME = b"RGTR"


class RegisterPackets(command.Packets):
    def __init__(self, name: str = None, email: str = None, password: str = None, data=None):
        self.name, self.email, self.password = name, email, password
        jdict = dict()
        if data is not None:
            jdict = json.loads(data)
            self.name, self.email, self.password = jdict["name"], jdict["email"], jdict["password"]
        elif name is not None and email is not None and password is not None:
            jdict = {
                "name": self.name,
                "email": self.email,
                "password": self.password,
            }
        super().__init__(name=REGISTER_PACKETS_NAME, message=bytes(json.dumps(jdict), encoding='ascii'))
