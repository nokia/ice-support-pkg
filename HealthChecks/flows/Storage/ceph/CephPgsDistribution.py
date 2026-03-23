from __future__ import absolute_import
from HealthCheckCommon.validator import InformatorValidator
from HealthCheckCommon.table_system_info import TableSystemInfo
from flows.Storage.ceph.Ceph import CephValidation
import tools.global_logging as gl
import math

from HealthCheckCommon.operations import *


class CephPgsDistribution(InformatorValidator, CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def __init__(self, ip):
        CephValidation.__init__(self, ip)

    def set_document(self):
        self._title = "Check CEPH PGs Distribution"
        self._unique_operation_name = "ceph_pgs_distribution"
        self._failed_msg = "The validation detected issues of PGs distribution for OSD/Pool"
        self._severity = Severity.NOTIFICATION
        self._system_info = ""
        self._table_system_info=TableSystemInfo(remarks="")
        self._title_of_info = "PGs Distribution per OSD and Pool"
        self._implication_tags = [ImplicationTag.PERFORMANCE]
        self._is_pure_info = False

    def is_validation_passed(self):
        finalStr = ''
        pgsRawData, osdRawData, poolsNames = self.gather_raw_data()
        dataDict = CephPgsDistribution.process_data_set(pgsRawData, osdRawData, poolsNames, self.get_host_ip())
        dataDict["finalStr"] = finalStr
        dataDict = CephPgsDistribution.display_table(dataDict)
        self._table_system_info.table = dataDict['table_system_info']
        isPassed, dataDict = self.checkWarning(dataDict)
        self._table_system_info.remarks = dataDict['remarks_table_system_info']

        return isPassed

    def checkWarning(self, dataDict):
        dataDict['remarks_table_system_info'] = ""
        isPassed = True
        # dataDict hold all
        osdsDict = dataDict["osdsDict"]  # results matrix :
        poolsList = []
        for poolId in dataDict["poolsSet"]:
            if poolId:
                poolsList.append(poolId)

        osdsList = []
        for osdId in dataDict["osdsSet"]:
            if osdId:
                osdsList.append(osdId)

        poolsStatistics = dataDict["poolsStatistics"]
        poolSum = dataDict["poolSum"]

        MIN_NUM_OF_PGS_TO_CHECK, DEVIATION_VALUE = 256, 4
        for poolID in poolsList:
            poolPgsSum = poolSum[str(poolID)]
            if poolPgsSum > MIN_NUM_OF_PGS_TO_CHECK:
                poolIdDictKey = CephPgsDistribution.getPoolDictKey(poolID)
                poolAvg = poolsStatistics[poolIdDictKey]["AVG"]
                poolStdev = poolsStatistics[poolIdDictKey]["STDEV"]
                minDeviationValue = math.floor(float(poolAvg) - DEVIATION_VALUE * float(poolStdev))
                maxDeviationValue = math.ceil(float(poolAvg) + DEVIATION_VALUE * float(poolStdev))
                for osdID in osdsList:
                    osdIdDictKey = CephPgsDistribution.getOSDDictKey(osdID)
                    if poolIdDictKey in osdsDict[osdIdDictKey]:
                        osdPgCount = osdsDict[osdIdDictKey][poolIdDictKey]

                        msg = ''
                        if osdPgCount < minDeviationValue:
                            msg = self._get_deviation_msg(osdPgCount, minDeviationValue, osdID, poolID,
                                                          'below minimum', poolPgsSum)
                        if osdPgCount > maxDeviationValue:
                            msg = self._get_deviation_msg(osdPgCount, maxDeviationValue, osdID, poolID,
                                                          'above maximum', poolPgsSum)
                        if msg != '':   # either of above cases
                            self._add_msg_to_data(msg, dataDict)
                            isPassed = False

        if not isPassed:
            msg = "\n{} triggered only when total PGs in pool > {} and allowed deviation is exceeded.\n" \
                  "Allowed deviation calculated as pool's OSDs average +- {} times the standard deviation."\
                .format(self._severity, MIN_NUM_OF_PGS_TO_CHECK, DEVIATION_VALUE)
            self._add_msg_to_data(msg, dataDict)

        return isPassed, dataDict

    def _get_deviation_msg(self, osd_pg_count, deviation_value, osd_id, pool_id, comparison_str, pool_pgs_sum):
        msg = '{}: Found PGs distribution issue for OSD: {}, Pool: {}, PGs: {} {} allowed deviation of {} PGs. ' \
              'Total PGs in pool: {}' \
            .format(self._severity, osd_id, pool_id, osd_pg_count, comparison_str, deviation_value, pool_pgs_sum)
        return msg

    def _add_msg_to_data(self, msg, data_dict):
        data_dict = CephPgsDistribution.print_and_log(msg, data_dict)
        data_dict['remarks_table_system_info'] += msg + '\n'

    @staticmethod
    def print_and_log(msg, dataDict):
        finalStr = dataDict["finalStr"]
        gl.log_and_print(msg)
        finalStr += msg + '\n'
        dataDict["finalStr"] = finalStr
        return dataDict

    def gather_raw_data(self):
        pgsRawDataCmd = 'sudo ceph pg dump -f json | jq "[.pg_map.pg_stats[] | {pgid, acting_primary}]"'

        if CephPgsDistribution.is_cbis_19_or_20():
            pgsRawDataCmd = 'sudo ceph pg dump -f json | jq "[.pg_stats[] | {pgid, acting_primary}]"'

        tmpLinesToProccess = self.get_output_from_run_cmd(pgsRawDataCmd, timeout=45, add_bash_timeout=True)

        if not tmpLinesToProccess:
            raise UnExpectedSystemOutput(self.get_host_ip(), pgsRawDataCmd, tmpLinesToProccess,
                                         "Failed to run cmd.")
        pgsRawData = json.loads(tmpLinesToProccess)  # {[Pg ID], [primary active OSD]}

        if len(pgsRawData) == 0:
            raise UnExpectedSystemOutput(self.get_host_ip(), pgsRawDataCmd, tmpLinesToProccess,
                                         "Expected to have at least 1 {[Pg ID] [primary active OSD]} in out list")
        osdRawData = self.get_osd_raw_data()
        poolsNames = self.get_pools_names()

        return pgsRawData, osdRawData, poolsNames

    def get_osd_raw_data(self):
        osdRawCmd = 'sudo ceph osd df 2>/dev/null'
        osdRawData = self.get_output_from_run_cmd(osdRawCmd, timeout=45, add_bash_timeout=True).splitlines()
        return osdRawData

    @staticmethod
    def get_pools_data(poolList, osdList, osdsDict):
        poolsDataSet = {}  # {"poolid":"osdsPgsList"}
        for osdID in osdList:
            osdIdDictKey = CephPgsDistribution.getOSDDictKey(osdID)
            for poolID in poolList:
                poolIdDictKey = CephPgsDistribution.getPoolDictKey(poolID)
                if poolIdDictKey in osdsDict[osdIdDictKey]:
                    pgsCount = osdsDict[osdIdDictKey][poolIdDictKey]
                    CephPgsDistribution.update_pools_data_set(poolID, poolsDataSet, pgsCount)

        return poolsDataSet

    @staticmethod
    def process_data_set(pgsRawData, osdRawData, poolsNames, host_ip):
        '''
         pgsRawData:
         list of lines, where each line is composed of 2 parameters, separated by a space:
         pgID primaryOSD
         exmaple:  3.1d7 29
        '''

        osdSum, osdsDict, osdsSet, poolSum, poolsSet = CephPgsDistribution.process_pgs_raw_data(pgsRawData, host_ip)
        poolList, osdList = CephPgsDistribution.sorting_data_for_display(poolsSet, osdsSet)
        poolsDataSet = CephPgsDistribution.get_pools_data(poolList, osdList, osdsDict)
        poolsStatistics = CephPgsDistribution.calculate_pools_statistics(poolList, poolsDataSet)
        osdSumOfSums = CephPgsDistribution.calculate_osdSumOfSums(osdList, osdSum)
        poolSumOfSums = CephPgsDistribution.calculate_poolSumOfSums(poolList, poolSum)

        dataDict = {"poolsSet": poolsSet,
                    "poolSum": poolSum,
                    "osdsSet": osdsSet,
                    "osdsDict": osdsDict,
                    "osdSum": osdSum,
                    "osdRawData": osdRawData,
                    "poolList": poolList,
                    "osdList": osdList,
                    "poolsStatistics": poolsStatistics,
                    "osdSumOfSums": osdSumOfSums,
                    "poolSumOfSums": poolSumOfSums,
                    "poolsNames": poolsNames,
                    "poolsDataSet": poolsDataSet}

        return dataDict

    @staticmethod
    def process_pgs_raw_data(pgsRawData, host_ip):
        osdsSet = {""}
        osdsDict = {}  # {"osdid":"poolid"}  # final analyzed data format : osds[ pool[ pgs count ] ]
        poolsSet = {""}
        poolSum = {}
        osdSum = {}
        for line in pgsRawData:
            osdID = str(line["acting_primary"])
            poolID = line["pgid"].split(".")[0]  # PG ID - 2.1fb , so left to the dot is the pool ID

            osdIdDictKey = CephPgsDistribution.getOSDDictKey(osdID)
            poolIdDictKey = CephPgsDistribution.getPoolDictKey(poolID)
            if osdIdDictKey in osdsDict:
                osdSum[osdID] += 1
                if poolIdDictKey in osdsDict[osdIdDictKey]:
                    currentPgsCount = osdsDict[osdIdDictKey][poolIdDictKey]
                    currentPgsCount += 1
                    osdsDict[osdIdDictKey][poolIdDictKey] = currentPgsCount
                else:
                    osdsDict[osdIdDictKey][poolIdDictKey] = 1
            else:
                osdsSet.add(osdID)
                osdSum[osdID] = 1
                osdsDict[osdIdDictKey] = {}  # {"poolid":"pgs counter"}
                osdsDict[osdIdDictKey][poolIdDictKey] = 1

            if poolID in poolsSet:
                poolSum[poolID] += 1
            else:
                poolsSet.add(poolID)
                poolSum[poolID] = 1
        return osdSum, osdsDict, osdsSet, poolSum, poolsSet

    @staticmethod
    def is_cbis_19_or_20():
        if (gs.get_version() == Version.V19A or gs.get_version() == Version.V20) and \
                gs.get_deployment_type() == Deployment_type.CBIS:
            return True
        return False

    def get_pools_names(self):
        poolsNamesCmd = 'sudo ceph osd lspools 2>/dev/null'
        if CephPgsDistribution.is_cbis_19_or_20():
            line = self.get_output_from_run_cmd(poolsNamesCmd,timeout=45, add_bash_timeout=True).strip()
            line = re.sub(',$', '', line)
            lines = line.split(',')
        else:
            lines = self.get_output_from_run_cmd(poolsNamesCmd,timeout=45, add_bash_timeout=True).strip().splitlines()
        return lines

    @staticmethod
    def calculate_pools_statistics(poolList, poolsDataSet):
        poolsStatistics = {}  # {"poolID":{"AVG":"average", "STDEV":"standard deviation"}}
        for poolID in poolList:
            poolIdDictKey = CephPgsDistribution.getPoolDictKey(poolID)
            # calculate Pool Average
            poolsPgsList = poolsDataSet[str(poolID)]
            avgVal = float(sum(poolsPgsList)) / len(poolsPgsList)
            avgVal = str(round(avgVal, 2))
            poolsStatistics[poolIdDictKey] = {"AVG": avgVal}

            # calculate Pool Standard deviation
            poolsPgsList = poolsDataSet[str(poolID)]
            stdevVal = PythonUtils.std(poolsPgsList)
            stdevVal = str(round(stdevVal, 2))
            poolIdDictKey = CephPgsDistribution.getPoolDictKey(poolID)
            poolsStatistics[poolIdDictKey]["STDEV"] = stdevVal

        return poolsStatistics

    @staticmethod
    def calculate_osdSumOfSums(osdList, osdSum):
        osdSumOfSums = 0
        for osdID in osdList:
            osdSumOfSums += osdSum[str(osdID)]

        return osdSumOfSums

    @staticmethod
    def calculate_poolSumOfSums(poolList, poolSum):
        poolSumOfSums = 0
        for poolID in poolList:
            poolSumOfSums += poolSum[str(poolID)]

        return poolSumOfSums

    @staticmethod
    def getOSDDictKey(osdID):
        return "OSD-" + str(osdID)

    @staticmethod
    def getPoolDictKey(poolID):
        return "POOL-" + str(poolID)

    @staticmethod
    def create_pools_statistics(poolList, poolsStatistics, dataDict):
        pools_statistics_list = []
        rowStr = "Avg    : \t\t"
        row_list = ["Avg    : "]
        # poolsStatictics - {"poolID":{"AVG":"average", "STDEV":"standard deviation"}
        for poolID in poolList:
            poolIdDictKey = CephPgsDistribution.getPoolDictKey(poolID)
            avgVal = poolsStatistics[poolIdDictKey]["AVG"]
            msg = "\t" + avgVal
            rowStr += msg
            row_list.append(avgVal)

        # htmlStr += '<td></td><td></td><td></td>'
        msg = '{}'.format(rowStr)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        pools_statistics_list.append(row_list + [' ', ' '])

        rowStr = "Stdev  : \t\t"
        row_list = ["Stdev  : "]
        for poolID in poolList:
            poolIdDictKey = CephPgsDistribution.getPoolDictKey(poolID)
            stdevVal = poolsStatistics[poolIdDictKey]["STDEV"]
            msg = "\t" + stdevVal
            rowStr += msg
            row_list.append(stdevVal)

        msg = '{}'.format(rowStr)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        pools_statistics_list.append(row_list + [' ', ' '])
        msg = ''
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        dataDict['table_system_info'].extend(pools_statistics_list)
        return dataDict

    ## display as table
    @staticmethod
    def display_table(dataDict):
        dataDict['table_system_info'] = []
        poolSum = dataDict["poolSum"]
        poolList = dataDict["poolList"]
        osdList = dataDict["osdList"]
        poolsStatistics = dataDict["poolsStatistics"]
        msg = ''
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        msg = 'PGs Distribution per OSD and Pool'
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        dataDict = CephPgsDistribution.create_pre_header(dataDict)
        seperatorLine, dataDict = CephPgsDistribution.create_tables_headers(poolList, dataDict)
        dataDict = CephPgsDistribution.create_table(poolList, osdList, dataDict)
        dataDict = CephPgsDistribution.create_pools_sum(poolList, poolSum, dataDict, seperatorLine)
        dataDict = CephPgsDistribution.create_pools_statistics(poolList, poolsStatistics, dataDict)
        return dataDict

    @staticmethod
    def sorting_data_for_display(poolsSet, osdsSet):
        # convert string set to numerically sorted list
        poolList = list(poolsSet)
        poolList.remove("")
        poolList = [int(i) for i in poolList]
        poolList.sort()
        osdList = list(osdsSet)
        osdList.remove("")
        osdList = [int(i) for i in osdList]
        osdList.sort()

        return poolList, osdList

    @staticmethod
    def create_tables_headers(poolList, dataDict):
        headers_pools_list = ["pool : "]
        headersStr = "pool : \t\t\t\t"
        seperatorLine = "----------------"
        for poolID in poolList:
            msg = str(poolID) + "\t"
            headersStr += msg
            headers_pools_list.append(poolID)
            seperatorLine += "-----------"
        headersStr += "\t| SUM\tUtilization(%)"
        headers_pools_list += ['SUM', 'Utilization(%)']

        msg = '{}'.format(headersStr)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        msg = '{}'.format(seperatorLine)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        dataDict['table_system_info'].append(headers_pools_list)
        return seperatorLine, dataDict

    @staticmethod
    def create_pre_header(dataDict):
        pre_header_list = [" "]
        lines = dataDict["poolsNames"]
        footerStr = "       \t\t\t\t"
        for line in lines:
            poolName = line.split(" ")[1]
            msg = '{}{}'.format(footerStr, poolName)
            pre_header_list.append(poolName)
            dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
            footerStr += ".\t"
        pre_header_list.extend([' ', ' '])
        dataDict['table_system_info'].append(pre_header_list)
        return dataDict

    @staticmethod
    def create_table(poolList, osdList, dataDict):
        pgs_per_osd_and_pool_list = []
        osdsDict = dataDict["osdsDict"]
        osdSum = dataDict["osdSum"]
        osdRawData = dataDict["osdRawData"]
        for osdID in osdList:
            osdClass = CephPgsDistribution.get_osd_disk_class(osdID, osdRawData)
            osdSize = CephPgsDistribution.get_osd_size(osdID, osdRawData)
            osdUtil = CephPgsDistribution.get_osd_utilization(osdID, osdRawData)

            rowStr = "osd{}.{}.\n{}".format(str(osdID), osdClass, osdSize)
            row_list = [rowStr]
            rowStr += " \t\t\t"
            for poolID in poolList:
                if "POOL-" + str(poolID) in osdsDict["OSD-" + str(osdID)]:
                    msg = str(osdsDict["OSD-" + str(osdID)]["POOL-" + str(poolID)]) + "\t"
                    rowStr += msg
                else:
                    msg = "0\t"
                    rowStr += msg
                row_list.append(msg)
            msg = "\t| " + str(osdSum[str(osdID)]) + "\t" + str(osdUtil)
            row_list.append(osdSum[str(osdID)])
            row_list.append(str(osdUtil))
            rowStr += msg

            msg = '{}'.format(rowStr)
            dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
            pgs_per_osd_and_pool_list.append(row_list)
        dataDict['table_system_info'].extend(pgs_per_osd_and_pool_list)
        return dataDict

    @staticmethod
    def get_osd_utilization(osdID, osdRawData):
        # retrive osd utilization
        # 'sudo ceph osd df 2>/dev/null'
        outtmp = osdRawData
        lineStartWithOsdIDPattern = '^[ ]*' + str(osdID) + '[ \t]'

        if CephPgsDistribution.is_cbis_19_or_20():
            # osdUtilCmd = 'sudo ceph osd df 2>/dev/null | grep -w "^[ ]*' + str(
            #    osdID) + '" | sed -E "s/[ ]+/ /g" | sed "s/^[ ]*//g" | cut -d " " -f8'
            for line in outtmp:
                if re.match(lineStartWithOsdIDPattern, line):
                    tmpline = " ".join(line.split())
                    osdUtil = tmpline.strip().split()[7]
        else:
            # osdUtilCmd = 'sudo ceph osd df 2>/dev/null | grep -w "^[ ]*' + str(
            #    osdID) + '" | sed -E "s/[ ]+/ /g" | sed "s/^[ ]*//g" | cut -d " " -f17'
            for line in outtmp:
                if re.match(lineStartWithOsdIDPattern, line):
                    tmpline = " ".join(line.split())
                    osdUtil = tmpline.strip().split()[16]

        return osdUtil

    @staticmethod
    def get_osd_size(osdID, osdRawData):
        # retrieve osd size
        # 'sudo ceph osd df 2>/dev/null'
        outtmp = osdRawData
        lineStartWithOsdIDPattern = '^[ ]*' + str(osdID) + '[ \t]'
        if CephPgsDistribution.is_cbis_19_or_20():
            # osdSizeCmd = 'sudo ceph osd df 2>/dev/null | grep -w "^[ ]*' + str(
            #    osdID) + '" | sed -E "s/[ ]+/ /g" | sed "s/^[ ]*//g" | cut -d " " -f5 | sed "s/G/_G/g" | sed "s/T/_T/g"'
            for line in outtmp:
                if re.match(lineStartWithOsdIDPattern, line):
                    tmpline = " ".join(line.split())
                    tmpline = tmpline.strip().split()[4]
                    osdSize = tmpline.replace('G', '_G').replace('T', '_T')
        else:
            # osdSizeCmd = 'sudo ceph osd df 2>/dev/null | grep -w "^[ ]*' + str(
            #    osdID) + '" | sed -E "s/[ ]+/ /g" | sed "s/^[ ]*//g" | cut -d " " -f5,6 | sed "s/ /_/g"'
            for line in outtmp:
                if re.match(lineStartWithOsdIDPattern, line):
                    tmpline = " ".join(line.split())
                    tmpline = tmpline.strip().split()[4] + ' ' + tmpline.strip().split()[5]
                    osdSize = tmpline.replace(' ', '_')

        return osdSize

    @staticmethod
    def get_osd_disk_class(osdID, osdRawData):
        # retrieve osd class - hdd/ssd/nvme
        # 'sudo ceph osd df 2>/dev/null'
        outtmp = osdRawData
        lineStartWithOsdIDPattern = '^[ ]*' + str(osdID) + '[ \t]'

        for line in outtmp:
            if re.match(lineStartWithOsdIDPattern, line):
                tmpline = " ".join(line.split())
                osdClass = tmpline.strip().split()[1]

        return osdClass

    @staticmethod
    def update_pools_data_set(poolID, poolsDataSet, pgsCount):
        if str(poolID) in poolsDataSet:
            (poolsDataSet[str(poolID)]).append(pgsCount)
        else:
            poolsDataSet[str(poolID)] = []
            (poolsDataSet[str(poolID)]).append(pgsCount)

    @staticmethod
    def create_pools_sum(poolList, poolSum, dataDict, seperatorLine):
        poolSumOfSums = dataDict["poolSumOfSums"]
        osdSumOfSums = dataDict["osdSumOfSums"]
        rowStr = "SUM  : \t\t\t"
        row_list = ["SUM  : "]

        for poolID in poolList:
            msg = "\t" + str(poolSum[str(poolID)])
            row_list.append(str(poolSum[str(poolID)]))
            rowStr += msg

        msg = "    \t\t" + str(poolSumOfSums) + "/" + str(osdSumOfSums)
        rowStr += msg
        row_list.append('{}/{}'.format(str(poolSumOfSums), str(osdSumOfSums)))
        msg = '{}'.format(seperatorLine)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        row_list.append(' ')
        msg = '{}'.format(rowStr)
        dataDict = CephPgsDistribution.print_and_log(msg, dataDict)
        dataDict['table_system_info'].append(row_list)
        return dataDict
