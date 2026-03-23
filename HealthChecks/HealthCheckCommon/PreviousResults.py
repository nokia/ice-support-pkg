previous_results = {}


def add_to_previous_results(command_name, result_details):
    global previous_results
    previous_results[command_name] = result_details


def check_commands_results_exist(command_names):
    for command in command_names:
        if command not in previous_results:
            return False
    return True


def get_all_collected_result():
    return previous_results


def get_validation_result_to_specific_host(required_command_name, host_name):
    for res in previous_results[required_command_name]["details"]:
        if host_name in res:
            return previous_results[required_command_name]["details"][res]

