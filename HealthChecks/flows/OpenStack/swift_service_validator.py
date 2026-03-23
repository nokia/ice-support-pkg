from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator
from tools.Exceptions import *
import tools.sys_parameters as gs


class SwiftServiceValidator(Validator):

    objective_hosts = [Objectives.UC]

    SCALE_INFO_PATH = '/home/stack/templates/scale-info.yaml'

    def set_document(self):

        self._unique_operation_name = "swift_list_output_to_nova_list_inventory"
        self._title = "Verify Swift is listing all containers related to overcloud nodes"
        self._failed_msg = "Swift container listing is in error"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def get_inventory(self):
        inventory = {}
        possible_flavor = []
        stream = self.get_output_from_run_cmd("cat {}".format(self.SCALE_INFO_PATH))
        scale_info = PythonUtils.yaml_safe_load(stream, file_path=self.SCALE_INFO_PATH)

        for key, value in list(scale_info['parameter_defaults'].items()):
            if key.endswith('Count'):
                inventory[key.rstrip('Count').lower()] = value
        # The values of inventory expected to be like {'Controller': 1, 'OvsCompute': 3}
        for key, value in list(scale_info['parameter_defaults'].items()):
            if key.endswith('Flavor'):
                possible_flavor.append(value.lower())
        # The output of possible flavor ie expected to be ['monitoring', 'ovscompute', 'sriovperformancecompute', 'controller', 'dpdkperformancecompute', 'avrscompute', 'storage']
        return inventory,possible_flavor

    def get_count_for_flavor(self, possible_flavor, output_list):
        flavor_counter_dict_1 = dict.fromkeys(possible_flavor,0)
        flavor_counter_dict = {('-' + k + '-'): v for (k, v) in list(flavor_counter_dict_1.items())}
    #    print ("flavor count dict {}".format(flavor_counter_dict))
        for key in flavor_counter_dict:
            for flavorname in output_list:
                if key in flavorname:
                    flavor_counter_dict[key] += 1
        return flavor_counter_dict

    def get_swift_output_lists(self,possible_flavor):
        cmd = "source {}; swift list".format(self.system_utils.get_stackrc_file_path())
        out = self.get_output_from_run_cmd(cmd)
        if not out:
            self._failed_msg = "Swift list command is not working, Critical system error"
            raise UnExpectedSystemOutput(ip='UC',
                                         cmd=cmd,
                                         output=out,
                                         message='Swift list not working - Failed, Exiting')
        swift_grep_ov = "source {}; swift list | grep ov- | jq -R -s -c 'split(\"\\n\")[:-1]'".format(self.system_utils.get_stackrc_file_path())
        exit_code, swift_output_grep_ov, err = self.run_cmd(swift_grep_ov, timeout=10)
        if not swift_output_grep_ov:
            raise UnExpectedSystemOutput(ip=self.get_host_name(), cmd=swift_grep_ov, output=swift_output_grep_ov,
                                         message='Swift list should contains "ov-" items, actual swift list:{}'.format(out.split()))
        swift_output_list = json.loads(swift_output_grep_ov)
        lowercase_swift_list = [item.lower() for item in swift_output_list]
    #    print("swift output list is {}".format(swift_output_list))
        # example of swift_output_list is ['ov-mxiqbwfatig-0-am2evrflk76k-OvsCompute-4iopoi7tbkv5', 'ov-mxiqbwfatig-1-6bf3x7km4q2n-OvsCompute-nvuvkfizz7kv', 'ov-mxiqbwfatig-2-2gcoka$ddjd5-OvsCompute-j4xv4em7bxnm', 'ov-sjpr63wdfkr-0-h5wf3y3elry5-Controller-2z5an7padtus']
        swift_possible_flavor_count = self.get_count_for_flavor(possible_flavor, lowercase_swift_list)
        return swift_possible_flavor_count
        # example of swift_possible_flavor_count is {'-avrscompute-': 0, '-storage-': 0, '-monitoring-': 0, '-ovscompute-': 1, '-dpdkperformancecompute-': 0, '-controller-': 1, '-sriovperformancecompute-': 1}"

    def get_nova_output_lists(self,possible_flavor):
        cmd2 = "source {}; openstack server list -c Name -f value".format(self.system_utils.get_stackrc_file_path())
        out2 = self.get_output_from_run_cmd(cmd2)
        nova_output_list = out2.lower().split()
    #    print("nova output list is {}".format(nova_output_list))
        # example of nova_output_list is ['overcloud-ovscompute-0', 'overcloud-controller-0', 'overcloud-ovscompute-2', 'overcloud-ovscompute-1']
        nova_count = self.get_count_for_flavor(possible_flavor, nova_output_list)
        # example of nova output is {'-avrscompute-': 0, '-storage-': 0, '-monitoring-': 0, '-ovscompute-': 1, '-dpdkperformancecompute-': 0, '-controller-': 1, '-sriovperformancecompute-': 1}
        return nova_count

    def is_validation_passed(self):
        current_inventory, flavor = self.get_inventory()
        current_swift_count = self.get_swift_output_lists(flavor)
        current_nova_count = self.get_nova_output_lists(flavor)

        # print('current_inventory:\n{}'.format(current_inventory))
        # print('current_swift_count:\n{}'.format(current_swift_count))
        # print('current_nova_count:\n{}'.format(current_nova_count))

        if current_swift_count == current_nova_count: #compare the whole dict`
            temp_dict1={x:y for x,y in list(current_swift_count.items()) if y!=0}
            temp_dict= { k.strip("-"): v for (k, v) in list(temp_dict1.items())}
    #        print ("temp dict is {}".format(temp_dict))
            #example of temp_dict {'controller': 1, 'ovscompute': 3}"
            if temp_dict == current_inventory:
                self._details = "Swift output is matching to nova output and inventory file at {}".format(self.SCALE_INFO_PATH)
                return True
            else:
                self._failed_msg = "Swift output and Nova output matching, but not with the inventory at {}\n" \
                                   "Swift / Nova output:\n{}\nInventory {} output:\n{}".\
                    format(self.SCALE_INFO_PATH, current_swift_count, self.SCALE_INFO_PATH, current_inventory)
        else:
            self._failed_msg = "Swift output not matching with Nova output:\n" \
                               "Swift output:\n{}\nNova output:\n{}".format(current_swift_count, current_nova_count)
        return False

class CheckSwiftDirectorySrv(Validator):

    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_swift_directory_srv"
        self._title = "Verify if directory /srv exists on undercloud"
        self._failed_msg = "Directory /srv doesn't exist on undercloud"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]


    def is_validation_passed(self):
        path = '/srv/'
        return self.file_utils.is_dir_exist(path)


class CheckSwiftFilesOvercloud(Validator):

    objective_hosts = [Objectives.UC]

    def set_document(self):

        self._unique_operation_name = "swift_mandatory_files-available_in_overcloud"
        self._title = "Verify Overcloud container has all mandatory files for scale operation"
        self._failed_msg = "Mandatory files are not listing.Check if files are present."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        CBIS_version = gs.get_version()
        if CBIS_version < Version.V22:
            required_files = [
                'bootstrap-config.yaml',
                'base-role-set.yaml',
                'all-nodes-validation.yaml'
            ]
            return self.check_all_files_exist(required_files)
        else:
            required_files = [
                'base-role-set.yaml'
            ]
            return self.check_all_files_exist(required_files)

    def check_all_files_exist(self,required_files):
            list_swift_files_cmd = "source {} ; swift list overcloud ".format(self.system_utils.get_stackrc_file_path())
            missing_files = []
            out = self.get_output_from_run_cmd(list_swift_files_cmd)
            swift_files = out.splitlines()
            for required_file in required_files:
                if required_file not in swift_files:
                    missing_files.append(required_file)
            if missing_files:
                self._failed_msg = "The following mandatory swift files are missing:\n{}".format('\n'.join(missing_files))
                return False
            return True


class CheckSrvDirOwner(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "is_srv_dir_owned_by_root"
        self._title = "is srv directory owned by root user or not"
        self._failed_msg = "/srv dir should be owned by root user and should be part of root group"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]


    def is_validation_passed(self):
        cmd = "sudo stat -c '%U %G' /srv"
        out = self.get_output_from_run_cmd(cmd, timeout=10)
        out_split = out.split()
        if out_split[0] != 'root' or out_split[1] != 'root':
            self._failed_msg = "/srv dir should be owned by root user and should be part of root group"
            return False
        return True


class ValidateSrvFolderSpace(Validator):
    objective_hosts = [Objectives.UC]
    SOFT_CONDITION = 80
    HARD_CONDITION = 90

    def set_document(self):
        self._unique_operation_name = "validate_srv_folder_space"
        self._title = "Validate /srv folder in UC is not full"
        self._failed_msg = "/srv folder in UC is full"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]


    def is_validation_passed(self):
        cmd = "df -h /srv"
        out = self.run_and_get_the_nth_field(cmd, n=12)
        space_used = self.parse_to_int(parm_to_parse=out.split('%')[0], cmd=cmd, out=out)
        if space_used > self.SOFT_CONDITION:
            condition = self.SOFT_CONDITION
            if space_used > self.HARD_CONDITION:
                condition = self.HARD_CONDITION
                self._severity = Severity.ERROR
            self._failed_msg += ", Over {condition}% of the folder full, space used:{space_used}%".format(
                condition=condition, space_used=space_used)
            return False
        return True
