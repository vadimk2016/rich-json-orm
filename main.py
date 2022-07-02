# -*- coding: utf-8 -*-

import json

from collections import defaultdict


QS_COMMANDS = ('exact', 'ne', 'gte', 'gt', 'lte', 'lt', 'in', 'nin', 'isnull')
qs_cache = defaultdict(dict)


class QuerySet:
    base_filters = None
    base_filters_exclude = None
    results = None
    source = None

    def __contains__(self, index):
        return index in self.results

    def __init__(self, base_filters=None, base_filters_exclude=None):
        self.results = []
        if base_filters:
            self.base_filters = base_filters
        if base_filters_exclude:
            self.base_filters_exclude = base_filters_exclude
        with open('source.json') as f_:
            self.source = json.load(f_)  # noqa

    def __nonzero__(self):
        return bool(self.results)

    def __str__(self):
        return 'QuerySet({})'.format(self.results)

    def __repr__(self):
        return 'QuerySet({})'.format(self.results)

    def __len__(self):
        return len(self.results)

    @staticmethod
    def check_command_condition(cmd, first, second):
        if cmd in 'exact':
            return first == second
        if cmd in 'ne':
            return first != second
        if cmd == 'gt':
            return first > second
        if cmd == 'gte':
            return first >= second
        if cmd == 'lt':
            return first < second
        if cmd == 'lte':
            return first <= second
        if cmd == 'in':
            return first in second
        if cmd == 'nin':
            return first not in second
        if cmd == 'isnull':
            return (first is None) == second

        raise ValueError('Cmd: "{}" not found'.format(cmd))

    def count(self):
        return len(self.results)

    def exclude(self, **kwargs):
        qs = self.get_new_qs()
        if not any(kwargs.values()):
            qs.results = self.results
            return qs
        if qs.base_filters_exclude:
            qs.base_filters_exclude.update(kwargs)
        else:
            qs.base_filters_exclude = kwargs
        qs.results = self._exclude_results(self.results, qs.base_filters_exclude)
        return qs

    def _exclude_results(self, results, kwargs):
        filters_number = len(kwargs)
        if not filters_number:
            return results
        to_remove = []
        for result in results:
            filters_passed = 0
            for filter_name, filter_value in kwargs.items():
                lookup, cmd = self.parse_filter(filter_name)
                attr_value = result.get(lookup)
                if attr_value and self.check_command_condition(cmd, attr_value, filter_value):
                    filters_passed = 1
            if filters_number == filters_passed:
                to_remove.append(result)  # .remove distorts the iteration
        return [r for r in results if r not in to_remove]

    def get_new_qs(self):
        return QuerySet(dict(self.base_filters or {}), dict(self.base_filters_exclude or {}))

    @staticmethod
    def parse_filter(f):
        filter_split = f.split('__')
        if 'or' in filter_split:
            filter_split.remove('or')
        elif 'ora' in filter_split:
            filter_split.remove('ora')
        cmds = set(QS_COMMANDS) & set(filter_split)
        if cmds:
            cmd = cmds.pop()
            filter_split.remove(cmd)
        else:
            cmd = 'exact'
        field_name = filter_split.pop()
        return field_name, cmd

    def filter(self, get_first_only=False, **kwargs):
        search_filters = dict(self.base_filters or {})
        search_filters.update(kwargs)

        qs_cache_key = str(search_filters)
        qs_cached = qs_cache.get(qs_cache_key)
        if qs_cached is not None:
            return qs_cached

        qs = self.get_new_qs()
        qs.base_filters = search_filters

        filters_number = 0
        filters_number_or = 0
        filters_number_ora = 0
        lookups_parsed = {}
        lookups_conditionals = {}
        for lookup in search_filters:
            lookups_parsed[lookup] = self.parse_filter(lookup)
            if '__' not in lookup:
                filters_number += 1
                continue
            v = lookup[-3:]
            if v == '_or':
                lookups_conditionals[lookup] = 'or'
                filters_number_or += 1
            elif v == 'ora':
                lookups_conditionals[lookup] = 'ora'
                filters_number_ora += 1
            else:
                filters_number += 1

        results = []
        for row in self.source:
            filters_passed = 0
            filters_passed_or = 0
            filters_passed_ora = 0

            for filter_k in search_filters:
                filter_v = search_filters[filter_k]

                is_or_filter = False
                is_ora_filter = False
                if filter_k in lookups_conditionals:
                    v = lookups_conditionals[filter_k]
                    if v == 'or':
                        if filters_passed_or:
                            continue
                        is_or_filter = True
                    elif v == 'ora':
                        is_ora_filter = True

                field_name, cmd = lookups_parsed[filter_k]
                if not field_name:
                    raise ValueError('Empty lookup')

                if self.check_command_condition(cmd, row[field_name], filter_v):
                    if is_or_filter:
                        filters_passed_or += 1
                    elif is_ora_filter:
                        filters_passed_ora += 1
                    else:
                        filters_passed += 1
                elif not is_or_filter and not is_ora_filter:
                    break

            if filters_number == filters_passed and (
                (not filters_number_or and not filters_number_ora) or
                (filters_passed_or or (filters_number_ora and filters_number_ora == filters_passed_ora))
            ):
                results.append(row)
                if get_first_only:
                    break

        if qs.base_filters_exclude:
            results = self._exclude_results(results, qs.base_filters_exclude)
        qs.results = results

        qs_cache[qs_cache_key] = qs
        return qs

    def first(self, **kwargs):
        try:
            return self.filter(get_first_only=True, **kwargs).results[0]
        except IndexError:
            return None

    def order_by(self, field):
        if field.startswith('-'):
            field = field.replace('-', '')
            is_reverse = True
        else:
            is_reverse = False
        qs = self.get_new_qs().filter()
        qs.results = sorted(qs.results, key=lambda d: d[field], reverse=is_reverse)
        return qs

    def values_list(self, attr_name):
        lookup, cmd = self.parse_filter(attr_name)
        return [d[lookup] for d in self.results]
