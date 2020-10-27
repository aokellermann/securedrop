import json

import securedrop.command as command

LOGIN_PACKETS_NAME = b"LGIN"


class LoginPackets(command.Packets):
    def __init__(self, email: str = None, password: str = None, data=None):
        self.email, self.password = email, password
        jdict = dict()
        if data is not None:
            jdict = json.loads(data)
            self.email, self.password = jdict["email"], jdict["password"]
        elif email is not None and password is not None:
            jdict = {
                "email": self.email,
                "password": self.password,
            }
        super().__init__(name=LOGIN_PACKETS_NAME, message=bytes(json.dumps(jdict), encoding='ascii'))
