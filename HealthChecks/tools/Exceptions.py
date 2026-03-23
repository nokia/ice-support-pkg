import inspect
import tools.user_params
from HealthCheckCommon.secret_filter import SecretFilter


def get_caller_info():
    """Find out the function and object that raised this exception."""
    stack = inspect.getouterframes(inspect.currentframe(), 2)
    for frame in stack:
        local_vars = frame.frame.f_locals if hasattr(frame, 'frame') else frame[0].f_locals
        if "self" in local_vars and hasattr(local_vars["self"], "is_clean_cmd_info"):
            return local_vars["self"]
    return None


def update_exception_attributes(exception_object, caller):
    attributes_list = ["cmd", "output", "message"]
    is_clean_info = caller and caller.is_clean_cmd_info() and not tools.user_params.debug_validation_flag
    if tools.user_params.debug_validation_flag:
        return
    is_sensitive_cmd = hasattr(exception_object, "cmd") and not is_clean_info and SecretFilter.is_encrypted(
        SecretFilter.filter_string_array(getattr(exception_object, 'cmd')))
    for attribute in attributes_list:
        if hasattr(exception_object, attribute):
            value = getattr(exception_object, attribute)
            if is_clean_info:
                value = "** {} is not available here for this validation **".format(attribute)
            elif is_sensitive_cmd:
                value = SecretFilter.encrypt_string(value)
            else:
                value = SecretFilter.filter_string_array(value)
            setattr(exception_object, attribute, value)


class HostNotReachable(Exception):
    '''Exception raised for reachability problems.
    Attributes:
        ip      -- ip of host
        message -- explanation of the error
        details -- more details about the error
    '''

    def __init__(self, ip, message=" host is not reachable", details=''):
        Exception.__init__(self, message)
        self._host_ip = ip
        self.message = message
        self.details = details

    def __str__(self):
        return "\nIP:{IP}: {message}-{details}".format(
            IP=self._host_ip,
            message=self.message,
            details=self.details)


class UnExpectedSystemOutput(Exception):
    '''Exception raised for un-expected execution output.
    Attributes:
        ip      -- ip of host
        output  -- the execution invalid output
        message -- more details about the error
    '''

    def __init__(self, ip, cmd, output, message='Un-Expected output', full_trace=""):
        Exception.__init__(self, message)
        self._host_ip = ip
        self.output = output
        self.message = message
        self.cmd = cmd
        self.full_trace = full_trace
        update_exception_attributes(self, get_caller_info())

    def __str__(self):
        return "\n-IP: {IP}\n -Command: {cmd}\n -Output: {out}\n -Message: {msg} \n -Trace: {trace}".format(
            IP=self._host_ip,
            cmd=self.cmd,
            out=self.output,
            msg=self.message,
            trace=self.full_trace
        )


class UnExpectedSystemOutputSize(UnExpectedSystemOutput):
    def __init__(self, ip, cmd, current_size, max_available_size, message='Un-Expected size output', full_trace=""):
        UnExpectedSystemOutput.__init__(self, ip, cmd, "", message, full_trace)
        self.current_size = current_size
        self.max_available_size = max_available_size

    def __str__(self):
        return "\n-IP: {IP}\n -Command: {cmd}\n -Output size: {out_size}\n" \
               " -Max available size: {max_available_size}\n " \
               "-Message: {msg} \n -Trace: {trace}".format(IP=self._host_ip,
                                                           cmd=self.cmd,
                                                           out_size=self.current_size,
                                                           max_available_size=self.max_available_size,
                                                           msg=self.message,
                                                           trace=self.full_trace
                                                           )


class UnExpectedSystemTimeOut(UnExpectedSystemOutput):
    def __init__(self, ip, cmd, timeout, output="", message='Un-Expected time out while running system cmd'
                 , full_trace="", exited_from=None):
        if exited_from:
            message += ". exited from {}.".format(exited_from)
        UnExpectedSystemOutput.__init__(self, ip, cmd, output, message, full_trace)
        self.timeout = timeout

    def __str__(self):
        return UnExpectedSystemOutput.__str__(self) + "\n-Timeout:{}".format(self.timeout)


class NonIdenticalValues(UnExpectedSystemOutput):
    def __init__(self, ip, cmd, values_output, message='Un-Expected output - All values should be the same', full_trace=""):
        UnExpectedSystemOutput.__init__(self, ip, cmd, values_output, message, full_trace)
        self.actual_values = values_output

    def __str__(self):
        return UnExpectedSystemOutput.__str__(self) + "\n-Actual Values: {}".format(self.actual_values)


class NotSupportedForThisVersion(Exception):
    '''Exception raised for validation that is not supported for this version
    Attributes:
        ip      -- ip of host
        output  -- the execution invalid output
        message -- more details about the error
    '''

    def __init__(self, cmd, message='validation is not supported for this version'):
        Exception.__init__(self, message)
        self.message = message
        self.cmd = cmd
        update_exception_attributes(self, get_caller_info())

    def __str__(self):
        return "Command: {cmd}\n\nMessage: {msg}".format(
            cmd=self.cmd,
            msg=self.message
        )


class LazyDataLoaderPreviousLoadProblem(Exception):
    def __init__(self, previous_exception, message='this validation decorated by lazy_global_data_loader.'
                                                   ' previous data load was failed', previous_trace=""):
        Exception.__init__(self, message)
        self.message = message
        self.previous_exception = previous_exception
        self.previous_trace = previous_trace

    def get_previous_exception(self):
        return self.previous_exception

    def __str__(self):
        return "Message:{msg} previous exception: {exception} previous_trace:{previous_trace}  " \
            .format(msg=self.message,
                    exception=self.previous_exception,
                    previous_trace=self.previous_trace)


class NoSuitableHostWasFoundForRoles(Exception):
    def __init__(self, roles=None, message=""):
        Exception.__init__(self, message)
        if roles is None:
            roles = []
        self.message = message + '\n no suitable host was found for the roles {}'.format(str(roles))

    def __str__(self):
        return "Message:{msg}".format(msg=self.message)


class NotApplicable(Exception):
    def __init__(self, message):
        self.message = 'This check is not applicable in this environment.\n' + message

    def __str__(self):
        return self.message


class InvalidDatetimeFormat(Exception):
    def __init__(self, date_and_time, datetime_format, exception):
        self.message = "{} - The date and time '{}' is invalid with format '{}'".format(exception, date_and_time, datetime_format)

    def __str__(self):
        return self.message


class InValidStringFormat(Exception):
    def __init__(self, s, regex=None):
        self.message = "string {} doesnt match the expected pattern \n{}".format(s, regex or "")

    def __str__(self):
        return self.message


class NoAvailableDiskSpace(Exception):
    def __init__(self, required_size, available_size, size_unit, path="/"):
        self.message = "There is not enough available disk space on '{path}'. \nRequired disk space: {required_size} {size_unit}\nAvailable disk space: {available_size} {size_unit}.".format(
            path=path, required_size=required_size, available_size=available_size, size_unit=size_unit)

    def __str__(self):
        return self.message


class IPHostMappingNotFoundError(Exception):
    def __init__(self, ip):
        self.message = "IP '{}' host name not found.\n Likely cause: 'sudo ifconfig | grep {}' returned no output check previous logs.".format(
            ip, ip)

    def __str__(self):
        return self.message
