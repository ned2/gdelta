import os
import re
import gzip
import codecs


class TsdbError(Exception):
    def __init__(self, msg):
        self.msg = msg


class TableReader:
    def __init__(self, name, path, rels):
        self.name = name
        self.rels = rels

        zip_path = path + '.gz'        
        if os.path.exists(zip_path):
            self.path = zip_path
            self.gzipped = True
        elif os.path.exists(path): 
            self.path = path
            self.gzipped = False
        else:
            raise TsdbError("Missing TSDB file: {}".format(name_name))

        if os.path.getsize(self.path) == 0:
            raise TsdbError("Empty TSDB file: {}".format(name_name))

    def open(self):
        if self.gzipped:
            return gzip.open(self.path)
        else:
            return open(self.path)

    def read_fields(self, text):
        text = text.decode('utf-8')
        field_values = text.strip().split('@')
        fields = {}
        for rel_name, (index, data_type) in self.rels.items():
            value = field_values[index]
            if value == '':
                value = None
            elif data_type == 'integer':
                value = int(value)
            fields[rel_name] = value
        return fields


class TsdbProfile:
    def __init__(self, path):
        self.path = path
        self.relations = self.get_relations()

    def get_relations(self):
        # dict of this form: { 'table_name' : { 'rel_name' : 'type' } } 
        relations = {}
        with open(os.path.join(self.path, 'relations')) as file:
            new_para = True
            for line in file:
                line = line.split('#')[0].rstrip()
                if line == '':
                    new_para = True
                elif new_para:
                    tsdb_file = line.rstrip(':')
                    relations[tsdb_file] = {}
                    counter = 0
                    new_para = False
                else:
                    fields = line.split(':')
                    name = fields[0].strip()
                    data_type = fields[1].strip()
                    relations[tsdb_file][name] = (counter, data_type)
                    counter += 1
        return relations

    def read_table(self, table_name):
        path = os.path.join(self.path, table_name)
        rels = self.relations[table_name]
        return TableReader(table_name, path, rels)


class Grammar:
    def __init__(self, alias):
        self.alias = alias

    def load(self, speech_prof):
        if self.tdl == "german.tdl":
            self.tdl = "common.tdl"
        self.tdl_path = os.path.join(self.path, self.tdl)
        self.get_tdl_files(speech_prof)
        self.load_types()
        self.load_lexicon()

    def get_tdl_files(self, speech_prof):
        self.tdl_files = []
        self.lex_files = []
        with open(self.tdl_path) as file:
            in_lex_section = False
            for line in file:
                line = line.strip()
                if line.startswith(':begin'):
                    section = line.strip('\n.').split()[-1] 
                    if section in ('lex-entry', 'generic-lex-entry'):
                        in_lex_section = True
                if line.startswith(':end'):
                        in_lex_section = False
                if line.startswith(':include'): 
                    tdl_file = line.split(':include')[1].strip('"\n. ')
                    if not tdl_file.endswith('.tdl'):
                        tdl_file += '.tdl'
                    tdl_file = os.path.join(*tdl_file.split('/'))
                    if in_lex_section:
                        self.lex_files.append(tdl_file)
                    else:
                        self.tdl_files.append(tdl_file)
        if speech_prof:
            self.lex_files.extend([os.path.join('speech', f) for f in 
                                   os.listdir(os.path.join(self.path, 'speech'))
                                   if f.endswith('.tdl')])

    def load_types(self):
        self.types = set()
        for tdl_file in self.tdl_files:
            with open(os.path.join(self.path, tdl_file)) as file:
                in_comment = False
                for line in file:
                    if line.startswith(';'):
                        continue
                    elif line.startswith('#|'):
                        in_comment = True
                        continue
                    elif line.startswith('|#'):
                        in_comment = False
                        continue
                    else:
                        if not in_comment and line.find(':=') > 0:
                            self.types.add(line.split(':=')[0].strip())

    def load_lexicon(self):
        self.lexicon = {}
        for lex_file in self.lex_files:
            path = os.path.join(self.path, lex_file)
            with codecs.open(path, 'r', 'utf-8') as file:
                for line in file:
                    parts = re.split(':=', line)
                    if len(parts) == 1:
                        continue
                    lex = parts[0].strip()
                    lex_type = parts[1].strip(' \n&')
                    self.lexicon[lex] = lex_type

    def load_lexicon_old(self, speech_prof):
        lex_files = ['lexicon.tdl']
        if self.grm == 'english.grm':
            lex_files.append('handon-propers.tdl')
            lex_files.append('gle.tdl')
            if speech_prof:
                lex_files.extend([os.path.join('speech', f) for f in 
                                  os.listdir(os.path.join(self.path, 'speech'))
                                  if f.endswith('.tdl')])
        elif self.grm == 'japanese.grm':
            lex_files.append('lex/tanaka-unknowns.tdl')
        elif self.grm == 'german.grm':
            lex_files.extend(['gen-lex.tdl', 'gen-lex-gen.tdl'])

        self.lexicon = {}
        for lex_file in lex_files:
            with open(os.path.join(self.path, lex_file)) as file:
                for line in file:
                    index = line.find(':=')
                    if  index != -1:
                        lex = line[:index - 1]
                        lex_type = line[index+3:-3]
                        self.lexicon[lex] = lex_type


def find_grammars(logonroot):
    grammars = {}
    reg_path = os.path.join(logonroot, 'etc', 'registry')
    with open(reg_path) as file:
        for line in file:
            char1 = line[0]
            if char1 in (';',' ','\n','t'):
                continue
            elif char1 == '[':
                alias = line.strip('[]\n')
                grammar = Grammar(alias)
                grammars[alias] = grammar
            else:
                key, value = line.strip().split('=')
                if key == 'rt':
                    grammar.path = os.path.join(logonroot, value)
                elif key == 'ne':
                    grammar.description = value
                elif key == 'vn':
                    grammar.version = value
                elif key == 'cp':
                    grammar.grm = value
                    grammar.tdl = value[:-4] + '.tdl'
    return grammars


# Currently used by gdelta
def get_profile_names(virtual_path, profile_alias):
    virt_prof_path = os.path.join(virtual_path, profile_alias, 'virtual')
    if os.path.exists(virt_prof_path):
        # profile is a virtual profile, find profile names
        with open(virt_prof_path) as file:
            return [p.strip('"\n') for p in file.readlines() if p !='\n']
    else:
        return [profile_alias]


def get_profile_path(profile_name, grammar_alias, gold):
    if gold:
        return os.path.join(TSDBHOME, 'gold', grammar_alias, profile_name) 
    else:
        # TODO
        return ''
