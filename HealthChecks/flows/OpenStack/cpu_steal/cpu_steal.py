from __future__ import absolute_import
from flows.OpenStack.cpu_steal.GuestValidator import *
import time

from tools.global_enums import Objectives, Severity, ImplicationTag
from six.moves import range

NANOSECONDS = 1000000000.0
MEASUREMENT_INTERVAL_SEC = 1
NUMBER_OF_MEASUREMENTS = 4
PASS_THRESHOLD_PERCENT = 10
CMD_GET_RAW_MEASUREMENT = "cat /proc/{}/schedstat"

class CPU_steal_validation(GuestValidator):
   
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._unique_operation_name = "cpu_steal_validation"
        self._title = "CPU steal time validation"
        self._failed_msg = "CPU steal is above {} %".format(PASS_THRESHOLD_PERCENT)
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PERFORMANCE]


    def is_validation_passed(self):
        is_pass = True
        VMs = self.getVirtualMachines()    

        for i in range(NUMBER_OF_MEASUREMENTS):
            self.getMeasurement(VMs)
            time.sleep(MEASUREMENT_INTERVAL_SEC)
    
        for vm in VMs:
            for vcpu in vm.vCPUs:
                old = None
                for measurement in vcpu.stealTimes:
                    sumOfCPUSteal = 0
                    if old != None:
                        sumOfCPUSteal += self.getCPUSteal(old, measurement)
                    else:
                        old = measurement
                numOfMeasurements = len(vcpu.stealTimes)
                assert numOfMeasurements > 0
                steal = sumOfCPUSteal / numOfMeasurements
                if steal >= PASS_THRESHOLD_PERCENT:
                    is_pass = False
                    self._failed_msg += " on VM {} it is {} %".format(vm.guestName, steal)
        return is_pass

    def getCPUSteal(self, measurement1, measurement2):
       """Returns cpu steal time

       arguments:
       measurement1 -- measurement object
       measurement2 -- measurement object
       """
       delta = measurement2.value - measurement1.value
       elapsed_time = measurement2.timestamp - measurement1.timestamp
       #assert elapsed_time > 0
       return delta / elapsed_time * 100

    def getMeasurement(self, VMs):
       """Iterates over each vCPU of each VM and takes a measurement
       """
       for vm in VMs:
           for vCPU in vm.vCPUs:
               measurement = int(self.run_and_get_the_nth_field(CMD_GET_RAW_MEASUREMENT.format(vCPU.PID), 2, separator=' ')) / NANOSECONDS
               vCPU.addMeasurement(int(time.time()), measurement)
    
