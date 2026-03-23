from __future__ import absolute_import
from flows.Blueprint.BlueprintDataCollectorsCommon import *
import tools.sys_parameters as sys_parameters


class CsfAddOn(BlueprintDataCollector):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]}    # same available on all masters

    def get_system_ids(self):
        return {1}

    def get_charts_versions(self):
        ncs_version = sys_parameters.get_version()
        cmd = "sudo helm list --output json"
        if ncs_version >= Version.V22:  # for NCS 22+ you need to specify the namespaces
            cmd += " -A"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool, add_bash_timeout=True)
        out_json = json.loads(out)

        if "Releases" in out_json:
            out_json = out_json["Releases"]

        res = []

        for chart in out_json:
            chart_data = {
                "name": chart.get("Name") or chart.get("name"),
                "version": chart.get("Chart") or chart.get("chart")
            }

            res.append(chart_data)

        return res


class CburVersion(CsfAddOn):

    def get_blueprint_objective_key_name(self):
        return "CBUR@version"

    def collect_blueprint_data(self, **kwargs):
        cbur_version = '----'
        charts_list = self.get_charts_versions()
        for chart in charts_list:
            if 'cbur' in chart['name']:
                cbur_version = chart['version']
                break

        return {cbur_id: cbur_version for cbur_id in self.get_ids()}


class BtelVersion(CsfAddOn):

    def get_blueprint_objective_key_name(self):
        return "BTEL@version"

    def collect_blueprint_data(self, **kwargs):
        btel_version = '----'
        charts_list = self.get_charts_versions()
        for chart in charts_list:
            if 'btel' in chart['name']:
                btel_version = chart['version']
                break

        return {btel_id: btel_version for btel_id in self.get_ids()}


class CitmVersion(CsfAddOn):

    def get_blueprint_objective_key_name(self):
        return "CITM@version"

    def collect_blueprint_data(self, **kwargs):
        citm_version = '----'
        charts_list = self.get_charts_versions()
        for chart in charts_list:
            if 'citm' in chart['name']:
                citm_version = chart['version']
                break

        return {citm_id: citm_version for citm_id in self.get_ids()}


class HarborVersion(CsfAddOn):

    def get_blueprint_objective_key_name(self):
        return "Harbor@version"

    def collect_blueprint_data(self, **kwargs):
        harbor_version = '----'
        charts_list = self.get_charts_versions()
        for chart in charts_list:
            if 'harbor' in chart['name']:
                harbor_version = chart['version']
                break

        return {harbor_id: harbor_version for harbor_id in self.get_ids()}


class IstioVersion(CsfAddOn):
    objective_hosts = [Objectives.ONE_MASTER]

    def get_blueprint_objective_key_name(self):
        return "Istio@version"

    def collect_blueprint_data(self, **kwargs):
        istio_version = '----'
        charts_list = self.get_charts_versions()
        for chart in charts_list:
            if 'istio' in chart['name']:
                istio_version = chart['version']
                break

        return {istio_id: istio_version for istio_id in self.get_ids()}


class FalcoVersion(CsfAddOn):

    def get_blueprint_objective_key_name(self):
        return "Falco@version"

    def collect_blueprint_data(self, **kwargs):
        falco_version = '----'
        charts_list = self.get_charts_versions()
        for chart in charts_list:
            if 'falco' in chart['name']:
                falco_version = chart['version']
                break

        return {falco_id: falco_version for falco_id in self.get_ids()}
