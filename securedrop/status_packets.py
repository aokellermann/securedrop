import json

import securedrop.command as command

STATUS_PACKETS_NAME = b"STAT"


class StatusPackets(command.Packets):
    def __init__(self, status=None, message=None, data=None):
        self.ok, self.message = status, message
        jdict = dict()
        if data is not None:
            jdict = json.loads(data)
            self.ok, self.message = jdict["ok"], jdict["message"]
        elif status is not None:
            jdict = {
                "ok": self.ok,
                "message": self.message,
            }
        super().__init__(name=STATUS_PACKETS_NAME, message=bytes(json.dumps(jdict), encoding='ascii'))
