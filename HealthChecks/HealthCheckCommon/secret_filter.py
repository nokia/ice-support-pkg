from __future__ import absolute_import
import re

from tools import python_versioning_alignment
from tools.SecurityHelper import generate_key, encrypt_message_by_key
from tools.python_versioning_alignment import get_unicode_type


class SecretFilter:

    tokens_of_secrets = [b"openssl",
                         b"-u root",
                         b"pass",
                         b"password",
                         b"rabbit",
                         b"--decode",
                         b"cookie hash",
                         b"secret",
                         b"admin_pwd",
                         b"ipmitool"
                         ]

    # Every pattern need to have 3 capture groups!
    patterns_of_secrets = [
        br"echo\s([a-zA-Z0-9=]*)\s\|\sbase64 -d.*$",
        # "openssl",
        br"mysql.* -p([a-zA-Z0-9]*)\s.*$",
        br"mysql.* -p\s([a-zA-Z0-9]*)\s.*$",
        br"\sX-Auth-Token:([a-zA-Z0-9_\\-]*)\s.*$",
        # "pass",
        # "password",
        # "--decode",
        # "cookie hash",
        # "pas", "ssh-rsa", "ssh", "rsa", "key", "dsa", "ecdsa", "pwd_value", "pwd",
        # "token", "#?\\s?token = "
        # "_token", "_password", "_key", "-key"
        # "secret",
        # :\/\/(?:[,]?[a-zA-Z]:[a-zA-Z0-9]@[a-zA-Z0-9\.]:[0-9]){3}\/
        br"://[a-zA-Z]*:([a-zA-Z0-9]*)@",  # this replaces the first occurrence ://user:password@host
        br"://.*,[a-zA-Z]*:([a-zA-Z0-9]*)@.*$",   # this replaces the second and third occurrence ://*,user:pass@host
        br"redis-cli.*\s-a\s'([a-zA-Z0-9]*)'"  # this replaces the  kubectl command that use mariadb user and pass:
        # "... redis-cli ... -a 'mariadb_pass' --user 'mariadb_user' ..."
    ]
    fernet_key = generate_key()
    ENCRYPTED_START_MSG = "--Encrypted msg start--"
    ENCRYPTED_END_MSG = "--Encrypted msg end--"

    @staticmethod
    def filter_string_array(input_string_array):
        str_flag = False
        if input_string_array is None:
            return input_string_array

        if isinstance(input_string_array, str) or isinstance(input_string_array, get_unicode_type()):
            input_string_array = [input_string_array]
            str_flag = True

        if isinstance(input_string_array, dict):
            return SecretFilter.filter_dict(input_string_array)

        assert isinstance(input_string_array,list)
        
        out_array = list()
        for line in input_string_array:
            if line is None:
                filtered = None
            else:
                filter_function = SecretFilter.get_filter_function(line)
                filtered = filter_function(line)

            out_array.append(filtered)

        return out_array if not str_flag else out_array[0]

    @staticmethod
    def get_filter_function(input):
        if isinstance(input, dict):
            return SecretFilter.filter_dict
        if isinstance(input, list):
            return SecretFilter.filter_string_array
        else:
            return SecretFilter.filter_string

    @staticmethod
    def filter_dict(input_dict):
        filtered_dict = {}
        for key, value in list(input_dict.items()):
            filter_function = SecretFilter.get_filter_function(key)
            filtered_key = filter_function(key)
            if value is None:
                filtered_value = None
            else:
                filter_function = SecretFilter.get_filter_function(value)
                filtered_value = filter_function(value)
            filtered_dict[filtered_key] = filtered_value
        return filtered_dict


    @staticmethod
    def filter_string(input_string):
        filtered = SecretFilter.filter_regex(input_string)
        filtered = SecretFilter.filter_basic(filtered)

        return filtered.decode()

    @staticmethod
    def filter_regex(input_string):
        ''' This function is replacing sensitive info with Regular Expressions.
            The idea is patterns are like: "prefixSENSITIVEpostfix". So to remove "SENSITIVE" patterns need to
            define 3 capture groups, the first and last are preserved, the middle ones are replaced. In the above
            example the output should be: "prefix*****postfix".
            The above method is needed, because without the capture groups, everything is replaced, not just the
            SENSITIVE part. '''
        if isinstance(input_string, int):
            input_string = str(input_string)
        if type(input_string) == python_versioning_alignment.get_unicode_type():
            input_string = input_string.encode('ascii', 'ignore')
        assert isinstance(input_string, str) or isinstance(input_string, bytes)

        out_string = input_string
        for pattern in SecretFilter.patterns_of_secrets:
            str_to_encrypt_list = re.findall(pattern, out_string)
            for msg_to_encrypt in str_to_encrypt_list:
                encrypted = SecretFilter._get_encrypted_encoded_msg(msg_to_encrypt)
                out_string = out_string.replace(msg_to_encrypt, encrypted)

        return out_string

    @staticmethod
    def encrypt_string(input_variable):
        value = SecretFilter._get_encrypted_encoded_msg(input_variable)
        return value.decode()

    @staticmethod
    def filter_basic(input_variable):
        #old implemantation - planed to be deprecated
        for token in SecretFilter.tokens_of_secrets:
            if token in input_variable:
                return SecretFilter._get_encrypted_encoded_msg(input_variable)

        return input_variable

    @staticmethod
    def _get_encrypted_encoded_msg(msg):
        encrypted = encrypt_message_by_key(msg, SecretFilter.fernet_key)
        str_res = SecretFilter.ENCRYPTED_START_MSG + encrypted.decode() + SecretFilter.ENCRYPTED_END_MSG

        return str_res.encode()

    @staticmethod
    def is_encrypted(content):
        encrypted_list = re.findall(r"{}.*?{}".format(SecretFilter.ENCRYPTED_START_MSG, SecretFilter.ENCRYPTED_END_MSG),
                                    content)
        if len(encrypted_list):
            return True
        return False