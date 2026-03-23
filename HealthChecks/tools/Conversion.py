from __future__ import absolute_import
from tools.global_enums import SubVersion


class Conversion:
    '''
    Class to convert different values: bytes to GiB or miles to km.
    '''
    KIBI_BYTE = 1024
    MEGA_BYTE = 1000000       # 1000**2
    MEBI_BYTE = 1048576       # 1024**2
    GIGA_BYTE = 1000000000    # 1000**3
    GIBI_BYTE = 1073741824    # 1024**3

    @staticmethod
    def convert_bytes_to_output_text(input_bytes):
        '''
        Calculates mebibytes and gibibytes. If value is lower than 1GiB, MiB is returned. Otherwise, GiB is returned.
        :param input_bytes: integer value of bytes
        :return: converted number and metric name <mebi|gibi>bytes
        '''
        input_bytes_megas = input_bytes / Conversion.MEBI_BYTE
        input_bytes_gigas = input_bytes / Conversion.GIBI_BYTE
        if input_bytes_gigas < 1:
            text_output = "{} mebibytes".format(input_bytes_megas)
        else:
            text_output = "{} gibibytes".format(input_bytes_gigas)
        return text_output

    def convert_bytes_to_mebibytes(self, input_bytes):
        '''

        :param input_bytes: integer number of bytes
        :return: integer number of bytes
        '''
        return input_bytes // self.MEBI_BYTE

    @staticmethod
    def convert_version_to_dict(hot_fix_version):
        sub_version_dict = dict()
        if 'MP' in hot_fix_version:
            sub_version_dict['MP_SP'] = 'MP' + hot_fix_version.split('MP')[-1].split('-')[0]
        elif 'SP' in hot_fix_version:
            sub_version_dict['MP_SP'] = 'SP' + hot_fix_version.split('SP')[-1].split('-')[0]
        else:
            sub_version_dict['MP_SP'] = SubVersion.NO_MP
        if 'PP' in hot_fix_version:
            sub_version_dict['PP_SU'] = 'PP' + hot_fix_version.split('PP')[-1].split('-')[0]
        elif 'SU' in hot_fix_version:
            sub_version_dict['PP_SU'] = 'SU' + hot_fix_version.split('SU')[-1].split('-')[0]
        else:
            sub_version_dict['PP_SU'] = SubVersion.NO_PP
        return sub_version_dict
