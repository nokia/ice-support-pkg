from __future__ import absolute_import
from __future__ import print_function
from collections import namedtuple
import tools.global_logging as log
import tools.user_params
from tools.OrderedConst import OrderedConst
from tools.global_enums import Severity

import json
import six
from six.moves import range

# used for priity print table
# taked from https://stackoverflow.com/questions/5909873/how-can-i-pretty-print-ascii-tables-with-python
# use by:

# >>> from collections import namedtuple
# >>> Row = namedtuple('Row',['first','second','third'])
# >>> data = Row(1,2,3)
# >>> data
# Row(first=1, second=2, third=3)
# >>> pprinttable([data])
# first = 1
# second = 2
# third = 3
# >>> pprinttable([data,data])
# first | second | third
# ------+--------+------
#    1 |      2 |     3
#    1 |      2 |     3
def pprinttable(rows):
    result_lines = []
    if len(rows) >= 1: #requsted for better look
        headers = rows[0]._fields
        lens = []
        for i in range(len(rows[0])):
            lens.append(len(max([x[i] for x in rows] + [headers[i]], key=lambda x: len(str(x)))))
        formats = []
        hformats = []
        for i in range(len(rows[0])):
            if isinstance(rows[0][i], int):
                formats.append("%%%dd" % lens[i])
            else:
                formats.append("%%-%ds" % lens[i])
            hformats.append("%%-%ds" % lens[i])
        pattern = " | ".join(formats)
        hpattern = " | ".join(hformats)
        separator = "-+-".join(['-' * n for n in lens])
        result_lines.append(hpattern % tuple(headers))
        result_lines.append(separator)
        _u = lambda t: t.decode('UTF-8', 'replace') if isinstance(t, six.binary_type) else t
        for line in rows:
            result_lines.append(pattern % tuple(_u(t) for t in line))
        result_lines.append(separator)
        result_lines.append("")

    #elif len(rows) == 1:
    #    row = rows[0]
    #    hwidth = len(max(row._fields, key=lambda x: len(x)))
    #    for i in range(len(row)):
    #        result_lines.append("%*s = %s" % (hwidth, row._fields[i], row[i]))
    text = "\n" + "\n".join(result_lines)
    log.log_and_print(text)


def print_details(msg_details):
    result_lines = []
    result_lines.append("Validation Failures\n")
    for validation_data in msg_details:
        result_lines.append("title: {}".format(validation_data['description_title'].strip('\n')))
        if validation_data.get('documentation_link') and tools.user_params.print_documentation_link:
            result_lines.append('documentation: {}'.format(validation_data.get('documentation_link')))
        if validation_data.get('describe_msg'):
            result_lines.append("{}".format(validation_data['describe_msg'].strip('\n')))

        if validation_data.get('exception'):
            result_lines.append("fail exception: {}".format(validation_data['exception'].strip('\n')))

        result_lines.append('')

    text = "\n" + "\n".join(result_lines)
    log.log_and_print(text)


def print_flows_result(flow, flg_only_failed, is_print_details=True):
    Row = namedtuple('Row', ['title', 'is_pass', 'describe_msg', 'severity'])
    details = flow['details']
    #if len(details) == 0:
    #    log.log_and_print("-- all is good here --")
    if flow.get('command_name') is None:
        log.log_and_print("Note: ")
        log.log_and_print(details)
        log.log_and_print("")
    else:
        log.log_and_print("***********************************************************")
        log.log_and_print("flow " + flow['command_name'] + ":")
        log.log_and_print("***********************************************************")
        for host in sorted(details):
            log.log_and_print('')
            log.log_and_print('AT HOST: ' + host + ":")
            log.log_and_print('')
            validations = details[host]
            flow_data = []

            msg_details = []
            for validation in validations:
                validation_data = validations[validation]
                description_title = validation_data['description_title']
                describe_msg = ""
                if validation_data.get('describe_msg'):
                    describe_msg = validation_data.get('describe_msg')
                if validation_data.get('documentation_link') and tools.user_params.print_documentation_link:
                    describe_msg += "\nDocumentation link:"+validation_data.get('documentation_link')
                #if validation_data.get('exception'):
                #    describe_msg = validation_data.get('exception')
                describe_msg = describe_msg or "---"

                severity = validation_data.get('severity', '---')
                cmd_info = validation_data.get('cmd_info', "---")

                if validation_data['pass'] is True:
                    is_pass = 'Yes'
                elif validation_data['pass'] is False:
                    is_pass = 'No'
                elif validation_data['pass'] is None:
                    is_pass = 'NA'
                else:
                    is_pass = str(validation_data['pass'])

                cmd_data = []

                if not flg_only_failed or not validation_data['pass']:
                    describe_msg = describe_msg.replace('\n', '|')
                    sentence_len = len(description_title) + len(is_pass) + len(describe_msg) + len(severity)
                    if sentence_len > 160 and validation_data['pass'] in [True, False]:
                        if is_print_details:
                            describe_msg = "description too long. please see 'details'"
                        else:
                            describe_msg = "description too long. The details can be found above"
                    if (validation_data['pass'] in [True, False] and sentence_len > 160) or (
                            validation_data['pass'] not in [True, False, "--"] and tools.user_params.debug_validation_name):
                        msg_details.append(validation_data)
                    data = Row(description_title, is_pass, describe_msg, severity)
                    flow_data.append(data)
                    # cmd_data.append("linux command used at "+ description_title +" : " + cmd_info + "\n")

            if len(flow_data) > 0:
                pprinttable(flow_data)
                # result_lines.append(cmd_data)
                print_validation_log(validations)
                if msg_details and is_print_details:
                    print_details(msg_details)
            else:
                log.log_and_print("-- all is well here---")

def print_validation_log(validations):
    if tools.user_params.debug_validation_name:
        for validation in validations:
            validation_data = validations[validation]
            if validation_data.get('validation_log'):
                information_validation = "information" if validation_data.get("system_info") is not None else "validation"
                cmd_output_title = "Commands output of {}: '{}':".format(information_validation,
                                                                         validation_data['description_title'])
                print('\n{}'.format(cmd_output_title))
                print('-' * len(cmd_output_title))
                for line in validation_data.get('validation_log'):
                    if type(line) is dict:
                        line = json.dumps(line, indent=4)
                    print('\t{}'.format(line))
                print('\n\n')


def print_minimum_json_out(failed_results):
    if len(failed_results) == 0:
        return
    to_print = {}
    for flow in failed_results:
        details = flow['details']
        for host in sorted(details):
            validations = details[host]
            for validation in validations:
                validation_data = validations[validation]
                description_title = validation_data['description_title']
                is_pass = validation_data.get('pass', '---')
                relevance_for_app = validation_data.get('relevance_for_app', 0)
                severity = validation_data.get('severity', '---')
                if description_title not in to_print:
                    to_print[description_title] = {'pass': is_pass,
                                                   'relevance_for_app': relevance_for_app,
                                                   'severity': severity}
                else:
                    if to_print[description_title]['relevance_for_app'] < relevance_for_app:
                        to_print[description_title]['relevance_for_app'] = relevance_for_app
                    if is_pass == 'NA':
                        to_print[description_title]['pass'] = 'NA'
                    elif is_pass == 'sys_problem' and to_print[description_title]['pass'] != 'NA':
                        to_print[description_title]['pass'] = 'sys_problem'

                    severity_level = OrderedConst.str2OrderedConst(Severity, severity)
                    to_print_severity = to_print[description_title]['severity']
                    to_print_severity_level = OrderedConst.str2OrderedConst(Severity, to_print_severity)
                    if severity_level < to_print_severity_level:
                        to_print[description_title]['severity'] = severity

    log.log_and_print("========================================================================")
    log.log_and_print("Summary of main failures in JSON:")
    log.log_and_print("========================================================================")
    log.log_and_print(json.dumps(to_print, indent=4))


def print_summarize_failures(failed_results, flg_only_failed):
    if len(failed_results):
        log.log_and_print("========================================================================")
        log.log_and_print("Summary of Failures:")
        log.log_and_print("========================================================================")
        for item in failed_results:
            print_flows_result(item, flg_only_failed, is_print_details=False)
