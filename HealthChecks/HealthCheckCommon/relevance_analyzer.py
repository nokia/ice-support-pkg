from __future__ import absolute_import
from tools.global_enums import ImplicationTag, Severity


class RelevanceAnalyzer:
    @staticmethod
    def update_validation_data_with_relevant_to_domain_field(severity, implication_tags, validation_data):
        relevant_to_domain_field_dict = {ImplicationTag.APPLICATION_DOMAIN: 'relevance_for_app'}
        domain_tag = RelevanceAnalyzer.get_domain_tag()
        relevance_for_domain = 0
        if implication_tags:
            if domain_tag in implication_tags:
                relevance_for_domain += 4
                if ImplicationTag.ACTIVE_PROBLEM in implication_tags:
                    relevance_for_domain += 3
            elif ImplicationTag.ACTIVE_PROBLEM in implication_tags:
                relevance_for_domain += 4
            elif ImplicationTag.PRE_OPERATION in implication_tags and ImplicationTag.ACTIVE_PROBLEM not in implication_tags:
                relevance_for_domain += 1
        if severity is Severity.ERROR:
            relevance_for_domain += 2
        if severity is Severity.CRITICAL:
            relevance_for_domain += 3
        relevance_for_domain = min(relevance_for_domain, 10)
        validation_data[relevant_to_domain_field_dict[domain_tag]] = relevance_for_domain
        return validation_data

    @staticmethod
    def get_domain_tag():
        return ImplicationTag.APPLICATION_DOMAIN
