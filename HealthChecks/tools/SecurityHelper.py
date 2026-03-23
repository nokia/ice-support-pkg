from __future__ import absolute_import
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


def load_key(key_path):
    with open(key_path, "rb") as f:
        res = f.read()

    return res


def encrypt_message_by_key_file(message, key_path):
    key = load_key(key_path)

    return encrypt_message_by_key(message, key)


def encrypt_message_by_key(message, key):
    if not isinstance(message, bytes):
        message = message.encode()
    fernet_key = Fernet(key)
    encrypted_message = fernet_key.encrypt(message)

    return encrypted_message


def decrypt_message_by_key_file(encrypted_message, key_path):
    key = load_key(key_path)

    return decrypt_message_by_key(encrypted_message, key)


def decrypt_message_by_key(encrypted_message, key):
    try:
        fernet_key = Fernet(key)
    except TypeError as e:
        raise TypeError("Please verify you didn't miss '=' at the end of key. Key is: {}. Exception is: {}".format(key,
                                                                                                                   e))
    decrypted_message = fernet_key.decrypt(encrypted_message)
    decoded_message = decrypted_message.decode()

    return decoded_message


def encrypt_msg_by_public_key_file(msg, key_full_path):
    with open(key_full_path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )

    encrypted = public_key.encrypt(
        msg,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )

    return encrypted


def decrypt_msg_by_private_key_file(msg, key_full_path):
    with open(key_full_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )

    original_message = private_key.decrypt(
        msg,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )

    return original_message


def generate_key():
    return Fernet.generate_key()
