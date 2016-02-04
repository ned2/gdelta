from __future__ import division
from collections import defaultdict

import math
import itertools

from profile import Profile


class Attribute:
    def __init__(self, name, prev_counts, new_counts, prev_parses, new_parses,
                 prev_types, new_types, weight_type):
        self.name = name
        self.prev_counts = prev_counts
        self.new_counts = new_counts
        self.change = new_counts - prev_counts
        self.change_size = abs(self.change)

        prev_idf = math.log((prev_parses + new_parses)/(1 + prev_counts) + 1)
        new_idf = math.log((new_parses + prev_parses)/(1 + new_counts) + 1)
        self.weight = abs(new_idf - prev_idf)

        if weight_type == 'count':
            self.cluster_weight = self.change_size
        elif weight_type == 'delta_idf2':
            self.cluster_weight = pow(self.weight, 2)
        else:
            self.cluster_weight = self.weight

        in_prev = name in prev_types
        in_new = name in new_types
        if in_prev and in_new:
            self.status = 'both'
        elif in_prev and not in_new:
            self.status = 'old'
        elif not in_prev and in_new:
            self.status = 'new'


class ParseCat:
    def __init__(self, title, desc, gopts):
        self.title = title
        self.desc = desc
        self.gopts = gopts
        self.items = {}

    def add_items(self, item_ids, profile):
        for i in item_ids:
            self.items[i] = profile[i]

    def finalize(self):
        self.used_items = [item for item in self.items.values() if item.used]
        self.num_total_items = len(self.items)
        self.num_used_items = len(self.used_items)
        self.num_unused_items = self.num_total_items - self.num_used_items
        self.attribute_counts = self.get_attribute_counts()

    def get_attribute_counts(self):
        attribute_counts = defaultdict(int)
        for item in self.used_items:
            for attribute in item.attributes:
                attribute_counts[attribute] += 1
        return attribute_counts

        
class Pdiff:
    def __init__(self, prev_gram, new_gram, profile_alias, profile_names, gopts):
        self.grammar_name = prev_gram.name
        self.prev_grammar = prev_gram
        self.new_grammar = new_gram
        self.profile_alias = profile_alias
        self.profile_names = profile_names
        self.gopts = gopts

        # parse change categories
        desc1 = "Items that previously did not parse but now do."
        desc2 = "Items that previously parsed but now do not."
        desc3 = "Items whose parsability did not change, but number of " \
            "readings did; attributes taken from the results of the previous " \
            "grammar."
        desc4 = "Items whose parsability did not change, but number of " \
            "readings did; attributes taken from the results of the new grammar."
        self.now_parses = ParseCat("no parse -> parse", desc1, gopts)
        self.now_no_parse = ParseCat("parse -> no parse", desc2, gopts) 
        self.still_parses_prev = ParseCat("*parse* -> parse", desc3, gopts)
        self.still_parses_new = ParseCat("parse -> *parse*", desc4, gopts)
        self.parse_cats = (self.now_parses, 
                           self.now_no_parse,
                           self.still_parses_prev,
                           self.still_parses_new)

        self.get_and_process_profiles()      
        for parse_cat in self.parse_cats:
            parse_cat.finalize()
        self.get_attributes()

    def get_and_process_profiles(self):
        self.profiles = {}
        self.item_list = []
        self.error_list = []
        self.prev_attribute_counts = defaultdict(int) 
        self.new_attribute_counts = defaultdict(int)
        self.num_items = 0
        self.prev_readings = 0
        self.new_readings = 0
        self.prev_parsing_items = 0
        self.new_parsing_items = 0
        self.prev_errors = 0
        self.new_errors = 0
        for profile_name in self.profile_names:
            prev = Profile(profile_name, self.prev_grammar, self.gopts)
            new = Profile(profile_name, self.new_grammar, self.gopts)
            self.profiles[profile_name] = (prev, new)
            self.num_items += len(prev.items) 
            self.prev_readings += prev.tot_readings
            self.new_readings += new.tot_readings
            self.calc_parse_changes(prev, new)
            self.add_attribute_counts(self.prev_attribute_counts, prev)
            self.add_attribute_counts(self.new_attribute_counts, new)
            self.process_items(prev, new)

    def process_items(self, prev, new):
        prev_values = prev.items.values()
        new_values = new.items.values()
        for prev_item, new_item in itertools.izip(prev_values, new_values):
            union_attributes = set(prev_item.attributes + new_item.attributes)
            self.item_list.append((prev_item, new_item, union_attributes))

            if prev_item.error != None:
                self.error_list.append(prev_item)
                self.prev_errors += 1
                if not prev_item.used:
                    new_item.used = False
            if new_item.error != None:
                self.error_list.append(new_item)
                self.new_errors += 1
                if not new_item.used:
                    prev_item.used = False

    def calc_parse_changes(self, prev, new):
        """
        Note that parse -> parse only includes those items whose
        number of readings has not changed.
        """
        self.prev_parsing_items += len(prev.has_readings)
        self.new_parsing_items += len(new.has_readings)
        still_parses = set(prev.has_readings).intersection(new.has_readings)
        still_parses = [i for i in still_parses 
                        if prev[i].tot_readings != new[i].tot_readings]
        now_parses = set(prev.no_readings).intersection(new.has_readings)
        now_no_parse = set(prev.has_readings).intersection(new.no_readings)

        self.now_parses.add_items(now_parses, new)
        self.now_no_parse.add_items(now_no_parse, prev)
        self.still_parses_new.add_items(still_parses, new)
        self.still_parses_prev.add_items(still_parses, prev)

    def add_attribute_counts(self, total_counts, this_profile):
        """Add the number of items each attribute occurs in """
        for item in this_profile.items.values():
            if item.used:
                for attribute in item.attributes:
                    total_counts[attribute] += 1

    def get_attributes(self):
        attributes = set(self.prev_attribute_counts.keys() + 
                       self.new_attribute_counts.keys())
        prev_parses = (self.now_no_parse.num_used_items + 
                       self.still_parses_prev.num_used_items)
        new_parses = (self.now_parses.num_used_items + 
                      self.still_parses_new.num_used_items)
        self.attributes = {}
        for attribute in attributes:
            self.attributes[attribute] = Attribute(attribute, 
                                             self.prev_attribute_counts[attribute], 
                                             self.new_attribute_counts[attribute], 
                                             prev_parses, new_parses, 
                                             self.prev_grammar.types, 
                                             self.new_grammar.types,
                                             self.gopts.weighting)
