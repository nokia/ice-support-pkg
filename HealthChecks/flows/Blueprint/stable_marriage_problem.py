from __future__ import absolute_import
# This solution was token from https://www.geeksforgeeks.org/stable-marriage-problem/
# Wiki: https://en.wikipedia.org/wiki/Stable_marriage_problem

from difflib import SequenceMatcher

from tools.python_utils import PythonUtils
from six.moves import range
from six.moves import zip


class StableMarriageProblem:
    def get_pairs(self, list_blueprint_dict, list_system_dict):
        list_blueprint_dict = [list_blueprint_dict] if type(list_blueprint_dict) != list else list_blueprint_dict
        list_system_dict = [list_system_dict] if type(list_system_dict) != list else list_system_dict
        n = max(len(list_blueprint_dict), len(list_system_dict))

        if abs(len(list_blueprint_dict) - len(list_system_dict)) > 0:
            empty_dicts = [dict() for _ in range(abs(len(list_blueprint_dict) - len(list_system_dict)))]
            if len(list_blueprint_dict) < len(list_system_dict):
                list_blueprint_dict = list_blueprint_dict + empty_dicts

            else:
                list_system_dict = list_system_dict + empty_dicts
        prefer, list_blueprint_dict = self._create_prefer_table(list_blueprint_dict, list_system_dict)
        pairs = self._stable_marriage(prefer, n)
        res = []

        for pair in pairs:
            res.append((list_blueprint_dict[pair[0]], list_system_dict[pair[1] - n]))

        return res

    # --------- Start Stable Marriage Algorithm ---------
    def _stable_marriage(self, prefer, n):
        woman_partner = [-1 for _ in range(n)]
        man_not_free = [False for _ in range(n)]

        free_count = n

        while free_count > 0:

            m = 0
            while m < n:
                if not man_not_free[m]:
                    break
                m += 1

            i = 0
            while i < n and not man_not_free[m]:
                w = prefer[m][i]

                if woman_partner[w - n] == -1:
                    woman_partner[w - n] = m
                    man_not_free[m] = True
                    free_count -= 1

                else:
                    m1 = woman_partner[w - n]
                    if not self._woman_prefers_m1_over_m(prefer, w, m, m1, n):
                        woman_partner[w - n] = m
                        man_not_free[m] = True
                        man_not_free[m1] = False
                i += 1

        return [(woman_partner[i], i + n) for i in range(n)]

    def _woman_prefers_m1_over_m(self, prefer, w, m, m1, n):
        for i in range(n):
            if prefer[w][i] == m1:
                return True

            if prefer[w][i] == m:
                return False

    # --------- End Stable Marriage Algorithm ---------

    def _create_prefer_table(self, list_blueprint_dict, list_system_dict):
        distances = self._create_distances_matrix(list_blueprint_dict, list_system_dict)

        distances_list, list_blueprint_dict = self._get_list_blueprint_distances_sorted_by_deviation(distances,
                                                                                                     list_blueprint_dict)
        prefer = []

        for distance in distances_list:
            system_dict_indexes = list(range(len(list_system_dict)))
            indexes_sorted_by_distance = sorted(system_dict_indexes, key=lambda k: distance[k])
            prefer.append(indexes_sorted_by_distance)

        return prefer, list_blueprint_dict

    def _get_list_blueprint_distances_sorted_by_deviation(self, distances, list_blueprint_dict):
        blueprint_dict_distances_pairs = list(zip(list_blueprint_dict, distances))
        blueprint_dict_distances_list = \
            sorted(blueprint_dict_distances_pairs, key=lambda pair: PythonUtils.std(pair[1]), reverse=True)
        list_blueprint_dict = []
        distances_list = []

        for (blueprint, distance) in blueprint_dict_distances_list:
            list_blueprint_dict.append(blueprint)
            distances_list.append(distance)

        return distances_list, list_blueprint_dict

    def _create_distances_matrix(self, list_blueprint_dict, list_system_dict):
        distances = []
        for blueprint_dict in list_blueprint_dict:
            blueprint_dict_distances = []
            for sys_dict in list_system_dict:
                blueprint_distances = self._get_distance(blueprint_dict, sys_dict)
                blueprint_dict_distances.append(blueprint_distances)
            distances.append(blueprint_dict_distances)
        return distances

    def _get_distance(self, blueprint_dict, sys_dict):
        scores = {"vendor": 1000,
                  "type": 100,
                  "version": 10}
        score = 0
        for name, value in list(blueprint_dict.items()):
            ratio = 1 - SequenceMatcher(None, str(value), str(sys_dict.get(name, ""))).ratio()
            score += ratio * scores.get(name, 1)

        return score
