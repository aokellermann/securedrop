import json

import securedrop.command as command

REGISTER_PACKETS_NAME = b"RGTR"


class RegisterPackets(command.Packets):
    def __init__(self, name=None, email=None, password=None, data=None):
        self.name, self.email, self.password = name, email, password
        jdict = dict()
        if data:
            jdict = json.loads(data)
            self.name, self.email, self.password = jdict["name"], jdict["email"], jdict["password"]
        elif name and email and password:
            jdict = {
                "name": self.name,
                "email": self.email,
                "password": self.password,
            }
        super().__init__(name=REGISTER_PACKETS_NAME, message=bytes(json.dumps(jdict)))
