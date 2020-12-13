from email_validator import validate_email, EmailNotValidError


def validate_and_normalize_email(email):
    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.email
    except EmailNotValidError as e:
        print(str(e))


class VerbosePrinter(object):
    _instance = None
    flag = False

    def __new__(cls, flag=None):
        if cls._instance is None:
            cls._instance = super(VerbosePrinter, cls).__new__(cls)
            if flag:
                cls.flag = True
            else:
                cls.flag = False
        return cls._instance

    def print(self, *data):
        if self.flag:
            print(data)
