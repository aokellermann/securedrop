from email_validator import validate_email, EmailNotValidError


def validate_and_normalize_email(email):
    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.email
    except EmailNotValidError as e:
        print(str(e))


class Verbose:
    flag: bool

    @classmethod
    def set(cls, option):
        cls.flag = option

    def print(self, data):
        if self.flag:
                print(data)

