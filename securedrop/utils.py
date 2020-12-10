import os

from Crypto.Hash import SHA256

from email_validator import validate_email, EmailNotValidError


def validate_and_normalize_email(email):
    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.email
    except EmailNotValidError as e:
        print(str(e))


def sha256_file(path: str):
    if not os.path.exists(path):
        return None

    with open(path, "rb") as file:
        hasher = SHA256.new()
        while chunk := file.read(256 * 16):
            hasher.update(chunk)

        return hasher.hexdigest()


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
