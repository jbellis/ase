import hashlib


def hexdigest(full_path):
    hash = hashlib.sha256()
    hash.update(open(full_path, 'rb').read())
    return hash.hexdigest()
