from __future__ import absolute_import
from __future__ import print_function
########################################################################################
# Anyone that want to contribute is welcome to imlement to this file
########################################################################################
########################################################################################
#method that are place holders for the real ones

import  subprocess

def get_the_n_th_field(out, n, separator=None):
    '''like awk {print $1} NOTE = starting from 1 (!)'''

    assert n >= 0, "in get_the_n_th_field asked for not existing field"

    if separator:
        field_list = out.split(separator)
    else:
        field_list = out.split()

    assert n <= len(
        field_list), "in get_the_n_th_field asked for not existing field (index is higher then the number of field"

    return field_list[n - 1]

    #methods you can use (plaece holder to the methods we use) :

    def run_cmd(cmd, timeout=120):
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        exit_code = process.wait()
        return exit_code, stdout, stderr

    def get_output_from_run_cmd( cmd, timeout=120):
        return_code, out, err = run_cmd(cmd, timeout=120)
        if return_code == 0:
            return out
        else:
            raise OSError(err)

    def run_and_get_the_nth_field(self, cmd, n, separator=None, timeout=120):
        out = self.get_output_from_run_cmd(cmd, timeout)
        out = get_the_n_th_field(out, n, separator)
        return out

    def run_cmd_return_is_successful(self, cmd, timeout=120):
        return_code, out, err = run_cmd(cmd, timeout)
        if return_code == 0:
            return True
        else:
            self._set_cmd_info(cmd, timeout, return_code, out, err)
        return False

########################################################################################################################
#
# please document the folowing:
# A: what is this validation for ? what is to validate , we prefer small and acuret validations.
# B:on what deployment type this validation expected to run on (CBIS / NCS / NCS on BM and etc)
# C:on wich CBIS/NCS version this valdtion is for
# D: where this validation need to be run (UC, Controller, /all-nodes / master)
# E: what would you want to tell the user in case of a failed ?
# F: How severe is it ? (critical/error/worning)
# G: is this valdtion can affect the system ? (loud ?, configuration chang ?) - we prefer passive validation only

# NOTE: Valdtion must return True or False if it passed or not. please define very specfic valdtion

########################################################################################################################


def is_validation_passed():

 #implement here, using the methods above
 failed_msg = "put your message when failed here"
 is_pass = True #make this variable get True value if and only if the validation passed
 # your implemntation
 # your implemntation
 # your implemntation

 return is_pass,failed_msg

if __name__ == '__main__':
    is_pass, failed_msg = is_validation_passed()
    print("validation --put-your-validation-name-here-- passed: {} message {} ".format(is_pass, failed_msg))
