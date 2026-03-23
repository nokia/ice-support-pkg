from __future__ import absolute_import
from HealthCheckCommon.validator import Validator
from tools.Exceptions import UnExpectedSystemOutput

CMD_GET_GUEST_NAMES_AND_UUIDS = "sudo virsh list --uuid --name"
CMD_GET_GUEST_PID = "grep -r -a -l {} /proc/[0-9]*/cmdline"
CMD_GET_VCPU_PIDS = "grep -r -h -e 'CPU' /proc/{}/task/*/stat | cut -d' ' -f1"


class GuestValidator(Validator):

    def run_and_get_list(self, cmd):
        """Returns the multiline output of the command
        as a list. Each element of the list corresponds
        to a new line of the output.

        arguments:
        cmd -- string, arbitrary linux command or chain of commands
        """
        out = []
        output = self.get_output_from_run_cmd(cmd)
        output = output.split('\n')
        for element in output:
            if len(element) > 0:
                out.append(element)
        return out

    def getVirtualMachines(self):
        """Returns a list of VM objects, each representing a
        virtual machine running on the host.
        """
        VMs = []
        guests = self.run_and_get_list(CMD_GET_GUEST_NAMES_AND_UUIDS)
        for guest in guests:
            guestUUID, guestName = guest.split()
            guestPID = self.get_guest_pid(guestUUID)
            new_vm = VM(guestUUID, guestName, guestPID)
            new_vm.addVCPUs(self.getVCPUs(guestPID))
            VMs.append(new_vm)
        return VMs

   
    def getVCPUs(self, PID):
        """Returns a list with the process ids(PIDs) that corresponds
        to each vCPU inside the virtual machine whose process id
        was passed in as argument
        arguments:

        PID -- int, Process id of the virtual machine
        """
        return self.run_and_get_list(CMD_GET_VCPU_PIDS.format(PID))

    def get_guest_pid(self, guest_uuid):
        """Returns the process id (PID) of the virtual machine

        arguments:
        guest_uuid -- string, UUID of the virtual machine
        """
        exit_code, out, err = self.run_cmd(CMD_GET_GUEST_PID.format(guest_uuid))

        if exit_code != 0 and "No such file or directory" not in err:
            raise UnExpectedSystemOutput(self.get_host_ip(),
                                         CMD_GET_GUEST_PID.format(guest_uuid), out + err)

        split_out = out.split("/")

        if len(split_out) < 3 or not split_out[2].isnumeric():
            raise UnExpectedSystemOutput(self.get_host_ip(),
                                         CMD_GET_GUEST_PID.format(guest_uuid), out + err,
                                         "Expected format of /proc/<pid>/cmdline")

        return int(split_out[2])



    
class VM:
    def __init__(self, guestUUID, guestName, guestPID):
        self.guestUUID = guestUUID
        self.guestName = guestName
        self.guestPID = guestPID
        self.vCPUs = [] 

    def addVCPUs(self, PIDs):
        """Add a vCPUs to the VM

        arguments:
        PIDs -- list of int, PID of each vCPU"""
        for PID in PIDs:
            self.vCPUs.append(VCPU(PID))

class VCPU:
    def __init__(self, PID):
        self.PID = PID
        self.stealTimes = []

    def addMeasurement(self, timestamp, value):
        """Add a new measurement to the vCPU

        arguments:
        timestamp -- time, the moment the measurement was aken
        value -- float value
        """
        self.stealTimes.append(Measurement(timestamp, value))

class Measurement:
    def __init__(self, timestamp, value):
        self.timestamp = timestamp
        self.value = value

