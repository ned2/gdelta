#!/usr/bin/env python
# gdelta.py - a DELPH-IN tool for comparing grammar versions
# Copyright (c) 2012 Ned Letcher, Tim Baldwin, Rebecca Dridan
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# TODO: 
# * Try to isolate the errors signal in overview page to only be parsing errors 
#   and not gdelta errors
# * switch profile proccessing code over to use itsdb


"""
gDelta 

A program to expose information about the impact that changes made to
a DELPH-IN grammar has had on parser output between runs over selected
profiles.

Usage: gdelta.py [options] grammar_name grammarA grammarB profile

Where 'grammar_name' is the name that TSDB uses to refer to the
grammar (eg 'erg' or 'gg'), 'grammarA' and 'grammarB' are the labels
corresponding to the relevant grammar entries in the etc/registry file
and 'profile' is either a single TSDB profile name or the name of a
virtual profile. Currently virtual profiles must be located within a
'virtual' directory located within the TSDB database directory. gDelta
also supports reading gold profiles; see the --gold option for
details.

Grammars A and B are expected to be complete DELPH-IN grammars where B
is a copy of A but with at least some changes made.

The default behaviour is to write output files to the directory
'gdelta_out/' but this can be changed with the --outdir option.

gGelta will automaticaly locate the relevant TSDB profile results for
comparison using the given comamndline arguments. If there are more
than one set of results for a given grammar and profile, gdelta will
select the most recent.

gDelta requires Python 2.7. The SciPy module is also recommended for
faster clustering.

Options:

 -b N, --best=N
      Restricts results to top analyses for an item. Default is N = 1.

 -k N, --k=N 
      Specifies the maximum number of clusters to try.  Default
      is k = 6. If the number provided is lower than the number of
      items in any of the categories being clustered over, k is
      changed to the number of items in the category.

 -w weighting, --weight=weighting
      Specifies the type of weighting to use for clustering. Valid
      weighting options are 'delta_idf', 'delta_idf2 and
      'count'. delta_idf uses the change in inverse document
      frequency, delta_idf2 is the squared change in inverse document
      frequency, and 'count' uses the change in frequency of
      attributes. Default is delta_idf.
      
 --outdir=dir
      Specifies an alternate path to put output files.

 --no-clustering
      Skip the clustering and don't produce any corresponding output.

 --skip-errors
      This flag indicates that items containing errors should be excluded;
      this includes items whose parsability has changed due to an error
      (and would therefore be included the relevant parse change category).

 --gold
      Tells gDelta to use gold profiles for the respective grammars.
      gDelta will look in the tsdb/gold path of grammars A and B for
      the given profile(s). 

 --forcek 
      The default behaviour of gdelta is to select the optimal value
      of k for clustering. This option forces whatever value supplied
      to the -k option to be used instead. 

 --debug 
      Prints debugging information pertaining to clustering to
      standard out.

 --ask
      If multiple parse results are found for a profile this flag
      causes gDelta to prompt for which profile to use. Otherwise
      gDelta defaults to using the most recent set of results.

 -h, --help
      Show this help.
"""


import sys
import os
import getopt

from pdiff import Pdiff
from output import Output 

import logon
import profile
import cluster


class Usage(Exception):
    usage = "Usage: gdelta.py [options] grammar_name grammarA grammarB profile"
    help = "For help use -h or --help"

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return '\n'.join([self.msg, '', self.usage, self.help])


class Opts():
    script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    home = os.environ.get('HOME')
    logonroot = os.environ.get('LOGONROOT')
    tsdb_path = os.path.join(logonroot, 'lingo', 'lkb', 'src', 'tsdb', 'home')
    virtual_path = os.path.join(tsdb_path, 'virtual') 
    nbest = 1
    k = 6
    clustering = True
    use_errors = True
    forcek =  False
    ask_profile = False
    debug =  False
    gold = False
    weighting = 'delta_idf'
    out_dir =  'gdelta_out'


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            short_opts = 'b:k:w:r:o:h'
            long_opts = ['best=','k=', 'help', 'weight=', 'forcek', 'debug', 
                         'outdir=', 'no-clustering', 'skip-errors', 'ask', 'gold']
            opts, args = getopt.getopt(argv[1:], short_opts, long_opts)
        except getopt.error, err:
            raise Usage(err.msg)

        gopts = Opts()
        for opt,arg in opts:
            if opt in ('-h', '--help'):
                print __doc__
                return 0
            elif opt in ('-b', '--best'):
                if not arg.isdigit():
                    raise Usage('Best option requires an integer argument')
                gopts.nbest = int(arg)
            elif opt in ('-k', '--k'):
                if not arg.isdigit():
                    raise Usage('K option requires an integer argument')
                gopts.k = int(arg)
            elif opt in ('-w', '--weight'):
                if arg not in ('delta_idf', 'delta_idf2', 'count'):
                    msg = 'Weight argument must be one of "delta_idf", ' \
                        '"delta_idf2" or "count"'
                    raise Usage(msg)
                gopts.weighting = arg
            elif opt in('o', '--outdir'):
                gopts.outdir = arg
            elif opt in ('-g', '--gold'):
                gopts.gold = True
            elif opt == '--no-clustering':
                gopts.clustering = False
            elif opt == '--skip-errors':
                gopts.use_errors = True
            elif opt == '--forcek':
                gopts.forcek = True
            elif opt == '--debug':
                gopts.debug = True
            elif opt == '--ask':
                gopts.ask_profile = True

        len_args = len(args) 
        if len_args > 4:
            raise Usage("Too many arguments.")
        elif len_args < 4:
            raise Usage("Not enough arguments.")
   
    except Usage, err:
        print >>sys.stderr, err
        return 2

    gram_name = args[0]
    prev_alias = args[1]
    new_alias = args[2]
    profile_alias = args[3]
    grammars = logon.find_grammars(gopts.logonroot)

    try:
        prev_gram = grammars[prev_alias]
        new_gram = grammars[new_alias]
    except KeyError, err:
        msg = "Grammar {0} was not found in registry file."
        print >>sys.stderr, msg.format(err)
        print >>sys.stderr, "For help use -h or --help"
        return 2       

    prev_gram.name = new_gram.name = gram_name 
    if profile_alias.startswith('vm') or profile_alias.startswith('ec'):
        speech = True
    else:
        speech = False

    prev_gram.load(speech)
    new_gram.load(speech)
    profile_names = logon.get_profile_names(gopts.virtual_path, profile_alias)
    pdiff = Pdiff(prev_gram, new_gram, profile_alias, profile_names, gopts)
    
    if gopts.clustering:
        for parse_cat in pdiff.parse_cats:
            parse_cat.results = cluster.do_clustering(pdiff, parse_cat)

    output = Output(pdiff, gopts)
    output.do_output()

    return 0


if __name__ == "__main__":
    sys.exit(main())

