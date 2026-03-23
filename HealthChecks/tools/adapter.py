from __future__ import absolute_import
from tools.global_enums import Deployment_type, Version


_adapter_instance = None


def initialize_adapter_instance(deployment_type, version):
    global _adapter_instance

    if deployment_type == Deployment_type.CBIS:
        if version < Version.V24:
            _adapter_instance = OldNokiaAdapter()
        else:
            _adapter_instance = NokiaAdapter()

    elif Deployment_type.is_ncs(deployment_type):
        if version < Version.V22:
            _adapter_instance = OldNokiaAdapter()
        else:
            _adapter_instance = NokiaAdapter()

    else:
        assert False, "Unknown deployment type"


def init_adapter(validator):
    assert _adapter_instance, "Please init adapter instance before using it."

    _adapter_instance.init_adapter(validator)


def docker_or_podman():
    assert _adapter_instance, "Please init adapter instance before using it."

    return _adapter_instance.docker_or_podman()


def kubectl():
    assert _adapter_instance, "Please init adapter instance before using it."

    return _adapter_instance.kubectl()


class Adapter(object):
    def __init__(self):
        self._validator = None

    def init_adapter(self, validator):
        self._validator = validator

    def docker_or_podman(self):
        return "podman"

    def kubectl(self):
        raise NotImplementedError


class NokiaAdapter(Adapter):
    def kubectl(self):
        return "kubectl"


class OldNokiaAdapter(NokiaAdapter):
    def docker_or_podman(self):
        return "docker"
