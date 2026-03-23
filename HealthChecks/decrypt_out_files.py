from __future__ import absolute_import
from __future__ import print_function
import argparse
import base64
import os
import re
import json
import sys

from cryptography.fernet import InvalidToken
from six.moves import range

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ice", "lib"))

from HealthCheckCommon.secret_filter import SecretFilter
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths
from tools.SecurityHelper import decrypt_message_by_key, decrypt_msg_by_private_key_file

key = None


def decrypt_list(list_to_decrypt):
    assert type(list_to_decrypt) is list

    for i in range(len(list_to_decrypt)):
        if type(list_to_decrypt[i]) is list:
            list_to_decrypt[i] = decrypt_list(list_to_decrypt[i])
        elif type(list_to_decrypt[i]) is dict:
            list_to_decrypt[i] = decrypt_dict(list_to_decrypt[i])
        else:
            list_to_decrypt[i] = decrypt_str(str(list_to_decrypt[i]))

    return list_to_decrypt


def decrypt_dict(dict_to_decrypt):
    assert type(dict_to_decrypt) is dict

    for k in list(dict_to_decrypt.keys()):
        if type(dict_to_decrypt[k]) is list:
            dict_to_decrypt[k] = decrypt_list(dict_to_decrypt[k])
        elif type(dict_to_decrypt[k]) is dict:
            dict_to_decrypt[k] = decrypt_dict(dict_to_decrypt[k])
        else:
            dict_to_decrypt[k] = decrypt_str(str(dict_to_decrypt[k]))

    return dict_to_decrypt


def decrypt_json_file(file_to_decrypt):
    with open(file_to_decrypt, 'rb') as f:
        content = json.load(f)

    if type(content) is dict:
        return decrypt_dict(content)

    return decrypt_list(content)


def decrypt_one_file(file_to_decrypt):
    if file_to_decrypt.endswith(".json"):
        content = decrypt_json_file(file_to_decrypt)

    else:
        with open(file_to_decrypt, 'r') as f:
            content = f.read()
        content = decrypt_str(content)

    filename, file_extension = os.path.splitext(file_to_decrypt)
    filename += ".decrypted"
    file_path = filename + file_extension

    with open(file_path, 'w') as f:
        if file_to_decrypt.endswith(".json"):
            json.dump(content, f, indent=4)
        else:
            f.write(content)
    print("File {} was decrypted successfully :)\n decrypted file: {}.\n".format(file_to_decrypt, file_path))


def decrypt_str(content, is_encrypted_str=False):
    # find all strings between SecretFilter.ENCRYPTED_START_MSG SecretFilter.ENCRYPTED_END_MSG,
    # include the start and end messages, not include sub match.
    # e.g. "--Encrypted msg start--FIRSTENCRYPTIONMSG--Encrypted msg end-- some data
    # --Encrypted msg start--SECONDENCRYPTIONMSG--Encrypted msg end--" =>
    # ["--Encrypted msg start--FIRSTENCRYPTIONMSG--Encrypted msg end--",
    # "--Encrypted msg start--SECONDENCRYPTIONMSG--Encrypted msg end--"]
    encrypted_start_in_html = SecretFilter.ENCRYPTED_START_MSG.replace(" ", "&nbsp;")
    encrypted_end_in_html = SecretFilter.ENCRYPTED_END_MSG.replace(" ", "&nbsp;")
    encrypted_messages = re.findall(r"{}.*?{}".format(SecretFilter.ENCRYPTED_START_MSG, SecretFilter.ENCRYPTED_END_MSG),
                                    content) + re.findall(r"{}.*?{}".format(encrypted_start_in_html,
                                                                            encrypted_end_in_html), content)
    if is_encrypted_str and len(encrypted_messages) == 0:
        encrypted_messages = [content]

    for encrypted_full_msg in encrypted_messages:
        encrypted = encrypted_full_msg.replace(SecretFilter.ENCRYPTED_START_MSG, "")
        encrypted = encrypted.replace(SecretFilter.ENCRYPTED_END_MSG, "")
        encrypted = encrypted.replace(encrypted_start_in_html, "")
        encrypted = encrypted.replace(encrypted_end_in_html, "").encode()
        try:
            decrypted = decrypt_message_by_key(encrypted, key)
            if SecretFilter.ENCRYPTED_START_MSG in decrypted and SecretFilter.ENCRYPTED_END_MSG in decrypted:
                decrypted = decrypt_str(str(decrypted))

        except InvalidToken as e:
            print("Error | Failed to decrypt the encrypted message: {}, please verify you entered the correct key."
                  .format(encrypted))
            raise e

        content = content.replace(encrypted_full_msg, decrypted)
    return str(content)


def decrypt(key_str, private_key_path, dir_path=None, files_list=None, encrypted_str_list=None):
    global key
    res = None
    ft_configuration_full_path = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                           FileTrackerPaths.FILE_TRACKER_CONFIGURATIONS))

    with open(ft_configuration_full_path) as json_file:
        file_tracker_log_name = json.load(json_file)["shared"]["FILE_TRACKER_LOG_NAME"]
    if not (dir_path or files_list or encrypted_str_list):
        print("No files to decrypt.")
        exit(1)
    decoded_key = base64.b64decode(key_str)
    key = decrypt_msg_by_private_key_file(decoded_key, private_key_path)

    files_list = files_list or []

    if dir_path:
        dir_files = os.listdir(dir_path)
        dir_full_path_list = [os.path.join(dir_path, file_path) for file_path in dir_files]
        files_list += dir_full_path_list
    if encrypted_str_list:
        res = []
        for encrypted_str in encrypted_str_list:
            decrypt_content = decrypt_str(encrypted_str, is_encrypted_str=True)
            res.append(decrypt_content)
            print("String was decrypted successfully :)\n decrypted string: {}".format(decrypt_content))
    for file_path in files_list:
        if file_tracker_log_name in os.path.basename(file_path):
            print("Couldn't decrypt {}. please use --encrypted-str".format(file_path))
        else:
            decrypt_one_file(file_path)

    return res


def main():
    parser = argparse.ArgumentParser(description="Decrypt logs files by key.")
    parser.add_argument('-d', '--dir_path', type=str, help='Path to logs directory.', required=False, default=None)
    parser.add_argument('--encrypted-str', type=str, help='String to decrypt', required=False, action='append',
                        default=[])
    parser.add_argument('-f', '--file_path', type=str, help='Path to logs file, can add multiple paths. '
                                                            'e.g. -f /path/to/file1 -f /path/to/file2 ...',
                        action='append', required=False, default=[])
    parser.add_argument('-k', '--key_str', type=str, help='The key str.', required=True)
    parser.add_argument('-p', '--private_key_path', type=str, help='The private key file path.', required=True)
    args = parser.parse_args()
    dir_path = args.dir_path
    files_list = args.file_path
    encoded_key = args.key_str
    encrypted_str_list = args.encrypted_str
    decrypt(encoded_key, args.private_key_path, dir_path, files_list, encrypted_str_list)


if __name__ == '__main__':
    main()
