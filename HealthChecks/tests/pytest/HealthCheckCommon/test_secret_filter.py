from __future__ import absolute_import
import re
import pytest

from HealthCheckCommon.secret_filter import SecretFilter
from tools.SecurityHelper import decrypt_message_by_key


lines_to_secrets = [
    ("sudo openssl ...", ["sudo openssl ..."]),
    ("command -u root P@$$ ..", ["command -u root P@$$ .."]),
    ("command pass=dkjlu continue cmd", ["command pass=dkjlu continue cmd"]),
    ("password=jfdhj", ["password=jfdhj"]),
    ("command secret hgf", ["command secret hgf"]),
    ("cmd --decode utf-8", ["cmd", "--decode utf-8"]),
    ("cookie hash", ["cookie hash"]),
    ("secret=kkjghfd---fdf", ["secret", "=kkjghfd---fdf"]),
    ("echo gsdfhjh | base64 -d fgh", ["gsdfhjh"]),
    ("mysql zg sdfr -pdfsrfs dfxf", ["dfsrfs"]),
    ("mysql zg sdfr -p dfsrfs dfxf", ["dfsrfs"]),
    ("edsg esg X-Auth-Token:Adsh-JHj_jkj kjgj", ["Adsh-JHj_jkj"]),
    ("http://user:Password@host", ["Password"]),
    ("http://somedata,user:Password@host", ["Password"]),
    ("sudo kubectl exec -it  -n ncms -- redis-cli -h H -p 16992 -a mariadb_pass --user "
     "mariadb_user PING", ["mariadb_pass"])
]
lines = [row[0] for row in lines_to_secrets]


@pytest.mark.parametrize("line, list_of_secrets", lines_to_secrets)
def test_filter_string_array(line, list_of_secrets):
    encrypted_line = SecretFilter.filter_string_array(line)
    for secret in list_of_secrets:
        assert secret not in encrypted_line, "Secret: {} was found after encrypt: {}, the encrypted msg is: {}".format(secret, line, encrypted_line)


@pytest.mark.parametrize("line", lines)
def test_decryption(line):
    encrypted_line = SecretFilter.filter_string_array(line)
    decrypted_line = encrypted_line
    for encrypted_msg in re.findall(r"{}.*?{}".format(SecretFilter.ENCRYPTED_START_MSG,
                                                      SecretFilter.ENCRYPTED_END_MSG), encrypted_line):
        encrypted = encrypted_msg.replace(SecretFilter.ENCRYPTED_START_MSG, "")
        encrypted = encrypted.replace(SecretFilter.ENCRYPTED_END_MSG, "")
        decrypted = decrypt_message_by_key(encrypted.encode(), SecretFilter.fernet_key)
        decrypted_line = decrypted_line.replace(encrypted_msg, decrypted)

    assert decrypted_line == line, "Error | decrypted_line {} isn't equal to origin line {}".format(decrypted_line,
                                                                                                    line)

