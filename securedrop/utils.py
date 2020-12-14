import os

from Crypto.Hash import SHA256
import logging

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


def set_logger(verbose):
    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)
