from __future__ import division
from collections import defaultdict

import os
import re
import sys
import logon
import itertools


NEWNAMES = True


class ParseResult:
    def __init__(self, score):
        self.score = score
        self.attributes = set()

class Item:
    def __init__(self, item_id, text, wf, length, profile_name, grammar):
        self.id = item_id
        self.text = text
        self.wf = wf
        self.length = length
        self.profile_name = profile_name
        self.grammar = grammar
        self.tot_readings = 0 
        self.results = []
        self.used = True
        self.error = None

    @property
    def attributes(self):
        return list(itertools.chain(*(r.attributes for r in self.results)))


class ItemError(Exception):
    def __init__(self, kind, msg):
        self.kind = kind
        self.msg = msg


class DerivationError(Exception):
    def __init__(self, msg):
        self.msg = msg



class Profile:
    """
    Contains the results and information pertaining to the results of
    parsing a single TSDB profile 
    """
    def __init__(self, profile_name, grammar, gopts): 
        self.name = profile_name
        self.grammar = grammar 
        self.gopts = gopts
        self.tot_readings = 0
        self.unknown_reg = re.compile(r'_[a-z]_[0-9]-tc$')
        self.old_erg = False

        # lists of item ids
        # should these be sets?
        self.has_readings = []
        self.no_readings = []

        # dicts of {attribute : lex_counts}
        self.lex_type_counts = defaultdict(int)
        self.other_type_counts = defaultdict(int)

        # initialise grammar names and paths etc
        self.profile_path = self.get_profile_path()
        self.tsdb_profile = logon.TsdbProfile(self.profile_path)
        if self.grammar.name == 'erg' and self.grammar.version == '0907':
            self.old_erg = True
            self.old_rulenames = self.get_old_rulenames()

        # process the contents of the profile
        try:
            self.items = self.get_items()
            nbest_results = self.locate_nbest_results()
            self.process_results(nbest_results)
        except logon.TsdbError, err:
            print >>sys.stderr, err.msg
            print >>sys.stderr, "gDelta halted."
            sys.exit(2)

    def get_profile_path(self):
        def select_dirs(path, dirs):
            print "There is more than than one profile output in " \
                "{0}\nPlease select one of the following:".format(path)
            for i,d in enumerate(dirs):
                print "{0}) {1}".format(i+1, d)
            try:
                num = int(raw_input())
                choice = dirs[num-1]
            except ValueError, IndexError:
                print "That's not a valid option."
                select_dirs(path, dirs, msg=False)
            return choice

        if self.gopts.gold:
            path = os.path.join(self.grammar.path, 'tsdb', 'gold', self.name)
        else:
            path = os.path.join(self.gopts.tsdb_path, self.grammar.name, 
                             self.grammar.version, self.name)

        if os.path.exists(os.path.join(path, 'relations')):
            # support bare profiles not in standard yy-mm-dd/pet subdirectories
            profile_path = path
        else:
            try:
                dirs = sorted(os.listdir(path))
                if not self.gopts.ask_profile or len(dirs) == 1:
                    # if more than one set of results, choose most recent
                    date = dirs[-1]
                else:
                    date = select_dirs(path, dirs)
            except OSError, err:
                msg = "No such TSDB profile '{0}'"
                print >>sys.stderr, msg.format(err.filename)
                print >>sys.stderr, "For help use -h or --help"
                sys.exit(2)
            profile_path = os.path.join(path, date, 'ace') 
        return profile_path

    def __getitem__(self,id):
        return self.items[id]

    def get_items(self):
        """ Returns a dictionary of Items indexed by item ID.  first
            processes the item file for information about items in the
            profile then process the parse file to find the total
            number of readings.
        """
        items = {}
        tr = self.tsdb_profile.read_table('item')
        with tr.open() as f:
            for line in f:
                fields = tr.read_fields(line.strip())
                item_id = fields['i-id']
                items[item_id] = Item(item_id, fields['i-input'], 
                                      bool(fields['i-wf']), fields['i-length'],
                                      self.name, self.grammar)

        tr = self.tsdb_profile.read_table('parse')
        with tr.open() as f:
            for line in f:
                fields = tr.read_fields(line.strip())
                item = items[fields['i-id']] 
                item.tot_readings = fields['readings']
                error_msg = fields['error']

                if error_msg != None:
                    error = ItemError("parse", error_msg)
                    item.error = error
                    if not self.gopts.use_errors:
                        item.used = False
        return items

    def locate_nbest_results(self):
        """ 
        Find the n best scores for items that have readings
        and recored this information in the Item object. First
        find the score for each result then add the nbest results
        for each item to total results.
        """
        scores = defaultdict(list)
        tr = self.tsdb_profile.read_table('result')
        with tr.open() as f:
            for line in f:
                fields = tr.read_fields(line.strip())
                item_id = fields['parse-id']
                result_id = fields['result-id']
                flags = fields['flags']
                score = float(flags.strip('()').split()[-1])
                scores[item_id].append((score, result_id))

        # turns out the results for each item are already sorted
        # in the results file, so part of this is probably uneccesary 
        nbest_results = set()
        for item_id, item in self.items.iteritems():
            item_scores = scores[item_id]
            item.num_results = len(item_scores)
            item_scores.sort(reverse=True, key=lambda x:x[0])
            nbest_results.update([id for score, id in 
                                  item_scores[:self.gopts.nbest]])
            self.tot_readings += item.tot_readings
            
            if item.tot_readings > 0:
                self.has_readings.append(item_id)
            else:
                self.no_readings.append(item_id)
        return nbest_results

    def process_results(self, nbest_results):
        """
        Process the results file again, parsing the nbest results for
        each item and creating a Result item.  

        Since results are sorted by score, we could actually process
        the results file in one pass...
        """
        tr = self.tsdb_profile.read_table('result')
        with tr.open() as f:
            for line in f:
                fields = tr.read_fields(line.strip())
                item_id = fields['parse-id']
                result_id = fields['result-id']
                derivation = fields['derivation']
                flags = fields['flags']
                score = float(flags.strip('()').split()[-1])
                item = self.items[item_id]
                if result_id not in nbest_results:
                    continue
                try:
                    parse = parse_derivation(derivation)
                    result = ParseResult(score)
                    item.results.append(result)
                    self.add_result_attributes(parse, result, item)
                except DerivationError as err:
                    root_node = derivation.strip('(').split()[0]
                    msg = u"resultID: {0}, root node: {1}".format(result_id, 
                                                                 root_node)
                    error = ItemError("derivation", msg)
                    item.error = error
                    item.used = False
                                
    def add_result_attributes(self, parse, result, item):
        node, children = parse
        if children == []:
            try:
                lex_type = self.grammar.lexicon[node]
                self.lex_type_counts[lex_type] += 1
                result.attributes.add(lex_type)
            except KeyError, key:
                msg = u"lex item: '{0}'".format(node)
                error = ItemError("lexicon", msg)
                item.error = error
                item.used = False
        else:
            # Map old onto new rulename if necessary
            # Should try to not check for every node in the profile
            if NEWNAMES and self.old_erg:
                if node in self.old_rulenames:
                    node = self.old_rulenames[node]
                else:
                    if node[:4] != 'root':
                        msg = u"No new type found in mapping: {0} in {1}"
                        print msg.format(node, self.grammar.name)
            self.other_type_counts[node] += 1
            result.attributes.add(node)
            for child in children:
                self.add_result_attributes(child, result, item)

    def get_old_rulenames(self):
        old_rulenames = {}
        path = os.path.join(self.gopts.logonroot, 'lingo', 'erg', 'util', 
                            'rulenames')
        with open(path) as file:        
            for line in file:
                tokens = line.split()
                old_rulenames[tokens[0]] = tokens[1]
        return old_rulenames


def parse_derivation(der_string):
    der_string = der_string.replace('\\"', '__ESCAPEDQUOTE__')
    lparen, rparen = '()'
    open_re, close_re = re.escape(lparen), re.escape(rparen) 
    node_re = r'("[^"]+"|[^{0}{1}"]+)+'.format(open_re, close_re)       
    token_re = re.compile('{0}{1}|{2}'.format(open_re, node_re, close_re))
    # Walk through each token, updating a stack of trees. 
    # Where a token is either lparen + node or rparen.
    stack = [(None, [])] # list of (node, children) 
    for match in token_re.finditer(der_string): 
        token = match.group() 
        # Leaf node 
        if token[:2] == lparen + '"': 
            if len(stack) == 1: 
                parse_error(der_string, match, lparen) 
            stack.append(('leaf', []))
        # Beginning of a tree/subtree 
        elif token[0] == lparen: 
            if len(stack) == 1 and len(stack[0][1]) > 0: 
                parse_error(der_string, match, 'end-of-string') 
            atts = token[1:].strip().split() 
            if len(atts) > 1:
                node = atts[1]
            elif len(atts) == 1:
                node = atts[0]
            else:
                parse_error(der_string, match, 'empty-node') 
            stack.append((node, [])) 
        # End of a tree/subtree 
        elif token == rparen: 
            if len(stack) == 1: 
                if len(stack[0][1]) == 0: 
                    parse_error(der_string, match, lparen) 
                else: 
                    parse_error(der_string, match, 'end-of-string') 
            node, children = stack.pop() 
            if node != 'leaf':
                stack[-1][1].append((node, children)) 
      # check that we got exactly one complete tree. 
    if len(stack) > 1: 
        parse_error(der_string, 'end-of-string', rparen) 
    elif len(stack[0][1]) == 0: 
        parse_error(der_string, 'end-of-string', lparen) 
    else: 
        assert stack[0][0] is None 
        assert len(stack[0][1]) == 1 
    tree = stack[0][1][0] 
    return tree


def parse_error(string, match, expecting):
    # Construct a basic error message
    if match == 'end-of-string':
        pos, token = len(string), 'end-of-string'
    else:
        pos, token = match.start(), match.group()
    msg = 'Parsing error: expected %r but got %r\n%sat index %d.' % (
        expecting, token, ' '*12, pos)
    # Add a display showing the error token itself:
    s = string.replace('\n', ' ').replace('\t', ' ')
    offset = pos
    if len(s) > pos+10:
        s = s[:pos+10]+'...'
    if pos > 10:
        s = '...'+s[pos-10:]
        offset = 13
    msg += '\n%s"%s"\n%s^' % (' '*16, s, ' '*(17+offset))
    raise DerivationError(msg) 
