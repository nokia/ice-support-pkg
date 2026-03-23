import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import os.path
import GlobalLogging


class CbisManagerClient(object):
    def __init__(self, cbis_manager_user_name, cbis_manager_password, cbis_manager_ip, timeout):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.auth = requests.auth.HTTPBasicAuth(cbis_manager_user_name, cbis_manager_password)
        self.url = "https://{}/".format(cbis_manager_ip)
        self.timeout = timeout

    def _get(self, uri, parameters={}, headers={}, timeout=None):
        request_timeout = self.timeout if not timeout else timeout
        url = self.url + uri
        response = requests.get(
            auth=self.auth,
            url=url,
            params=parameters,
            headers=headers,
            timeout=request_timeout,
            verify=False
        )
        return self._handle_response(response, url)

    def _post(self, uri, headers={}, data={}, json_obj={}, timeout=None):
        request_timeout = self.timeout if timeout is None else timeout
        url = self.url + uri
        response = requests.post(
            auth=self.auth,
            url=url,
            headers=headers,
            data=data,
            json=json_obj,
            timeout=request_timeout,
            verify=False
        )
        return self._handle_response(response, url)

    def _delete(self, uri, headers={}, parameters={}, timeout=None):
        request_timeout = self.timeout if timeout is None else timeout
        url = self.url + uri
        response = requests.delete(
            auth=self.auth,
            url=url,
            params=parameters,
            headers=headers,
            timeout=request_timeout,
            verify=False
        )
        return self._handle_response(response, url)

    def _handle_response(self, response, url):
        GlobalLogging.log_debug('\n\t\tUrl:{}\n\t\tResponse:{}'.format(url, response.content))
        if response.ok:
            return response.content
        else:
            message = "CBIS Manager status code is {}. Check if cbis manager is running".format(response.status_code)
            if response.status_code in [401, 402]:
                message = 'CBIS Manager User Name or password are not correct.' \
                          ' please update it in conf.yaml '
            if response.status_code == 500:
                message = 'CBIS Manager does not respond, please restart it and try again'
            error = '\n{}\nRequest Url:{}Status Code:{}\nDescription:{}\n{}'.format(
                message,
                url,
                response.status_code,
                response.reason,
                response.content)
            GlobalLogging.log_debug(error)
            raise requests.RequestException(message)

    def get_server_status(self):
        response = self._get('api/manager/status')
        return json.loads(response)

    def get_plugins(self):
        response = self._get('api/plugins')
        return json.loads(response).get('plugins')

    def get_version(self):
        # valid for cbis 20 <
        response = self._get('api/manager/product_type')
        return json.loads(response).get('version')

    # TODO: compare with MD5 the file before and after upload
    def upload_file(self, file_name, file_path, content_type, timeout):
        headers = {
            'Content-type': content_type,
            'X-FILENAME': file_name
        }
        response = self._post('upload',
                              headers=headers,
                              data=open(file_path, 'rb'),
                              timeout=timeout)
        uploaded_file_path = '/opt/install/temp_files/{}'.format(file_name)
        if os.path.isfile(uploaded_file_path):
            return True, None
        return False, 'The uploaded file:{} is not exist on server'.format(uploaded_file_path)

    def install_plugin(self, plugin_file_name, timeout):
        response_str = self._post('api/plugins', json_obj={"name": plugin_file_name}, timeout=timeout)
        response = json.loads(response_str)
        if response.get('status') == 'FAIL':
            return False, response.get('error')
        return True, None

    def delete_plugin(self, plugin_name):
        response = self._delete('api/plugins', parameters={'name': plugin_name})
        response_dict = json.loads(response)
        if response_dict.get('status') == 'SUCCESS':
            return True
        return False

    def get_running_processes(self):
        # valid for cbis 20 <
        response = self._get('api/get_processes_running')
        return json.loads(response)

    def restart_server(self):
        # valid for cbis 20 <
        response = self._post('api/restart')
        response_dict = json.loads(response)
        if response_dict == ["success", 200]:
            return True
        return False

    # check if the plugin is currently running
    def is_plugin_active(self, plugin_name):
        uri = '/api/{}/isActive'.format(plugin_name)
        response = self._get(uri)
        return response == 'true'

    # state- check the result of the plugin last operation (success\fail\unknown\N/A-in case of first time)
    def get_plugin_state(self, plugin_name):
        uri = '/api/{}/state'.format(plugin_name)
        response = self._get(uri)
        return response

    def is_require_restart(self):
        # REQUIRES_RESTART -CBIS 18-19A
        # REQUIRES_MANAGER_RESTART -CBIS 20 +
        status = self.get_server_status()
        if status['status'] == 'REQUIRES_RESTART' or status['status'] == 'REQUIRES_MANAGER_RESTART':
            return True
        return False
