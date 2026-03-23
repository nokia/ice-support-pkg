from __future__ import absolute_import
from flows.Cbis.user_config_validator.user_config_checks import *
class VerifyRookCephHealth(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_rook_ceph_health"
        self._title = "With Rook storage enabled, Verify if the ceph cluster is in healthy state"
        self._failed_msg = "Ceph cluster is not in healthy state"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE]

    def is_prerequisite_fulfilled(self):
        check_rookceph_namespace = "sudo kubectl get namespaces -o jsonpath='{.items[?(@.metadata.name==\"rook-ceph\")].metadata.name}'"
        return_code, namespace, err = self.run_cmd(check_rookceph_namespace)
        if not namespace:
            return False
        else:
            if "rook-ceph" in namespace:
                return True
            else:
                return False

    def is_validation_passed(self):
        get_ceph_oam_pod_status = "sudo kubectl -n rook-ceph get pods -l app=ceph-oam -o=jsonpath='{.items[*].status.phase}'"
        pod_status = self.get_output_from_run_cmd(get_ceph_oam_pod_status)
        if pod_status == "Running":
            get_pod_name ="sudo kubectl -n rook-ceph get pods -lapp=ceph-oam -o jsonpath='{.items[0].metadata.name}'"
            pod_name = self.get_output_from_run_cmd(get_pod_name)
            get_ceph_health = "sudo kubectl -n rook-ceph exec -it {} -c ceph-oam -- ceph health".format(pod_name)
            rook_health = self.get_output_from_run_cmd(get_ceph_health,add_bash_timeout=True)
            rook_health = str(rook_health).strip()
            if "HEALTH_OK" in rook_health:
                return True
            else:
                return False
        else:
            self._failed_msg = "ceph-oam pod is not running"
            return False

