import math
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

    chunk_size = 256 * 16
    total_chunks = os.path.getsize(path) / math.ceil(chunk_size)
    chunks_so_far = 0

    def print_hash_progress():
        print_status(*get_progress(chunks_so_far, total_chunks, chunk_size), "hashed")

    print_hash_progress()
    with open(path, "rb") as file:
        hasher = SHA256.new()
        while chunk := file.read(chunk_size):
            hasher.update(chunk)
            chunks_so_far += 1
            if chunks_so_far % 10 == 0:
                print_hash_progress()

        print_hash_progress()
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


def get_progress(chunks_so_far, total_chunks, chunk_size):
    chunks_so_far *= chunk_size
    total_chunks *= chunk_size
    percent = 100 * (chunks_so_far / total_chunks) if total_chunks else 0
    return sizeof_fmt(chunks_so_far), sizeof_fmt(total_chunks), "{}%".format(int(percent))


def print_status(progress, total, percent, verb):
    print("{}/{} {} ({})".format(progress, total, verb, percent), end='\r', flush=True)
