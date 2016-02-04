gDelta README file
Author: Ned Letcher
Date: 2012-10-09


WHAT IS IT?

gDelta is a tool that aims to provide more immediate feedback on the
impact of changes made to DELPH-IN grammars by comparing parser output
from two different states of a grammar. gDelta can be thought of as
functioning similar to a diff tool, allowing the comparison of two
different versions of the same grammar, but rather than comparing the
source code of the grammars it compares parser output from both
versions run over the same profiles.

gDelta makes use of a feature weighting algorithm for highlighting
features in the grammar that have been strongly impacted by a
modification to the grammar, as well as a technique for performing
clustering over profile items, which is intended to locate related
groups of change. These two techniques are used to build an HTML
interface which can be viewed offline.

By providing a high-level picture of the impact that modifications to
the grammar has had, the hope is that grammar engineers can use
gDelta to more readily check if anything unexpected has happened as
well as confirm that desired changes have taken effect, earlier rather
than later in the grammar development cycle.

Other applications of gDelta that have been suggested are:

 * Grammar documentation and the exploration of linguistic phenomena
   via investigating the impact of systematically switching off types.

 * A means of tracking uncaught regressions by comparing successive
   previous version of a grammar.

gDelta was created by Ned Letcher, Tim Baldwin and Rebecca Dridan.


INSTRUCTIONS

1) As per usual, make sure the $LOGONROOT environment variable is set
   with the path to your logon installation.

2) gDelta assumes that you have two distinct grammars (let's call them
   A and B), where B is a complete copy of grammar A's directory with
   at least one change made to a TDL file.

3) Both grammars A and B require entries in the
   $LOGONROOT/etc/registry file so gDelta knows where they live and
   what to call them.

5) Before you can use gDelta you also need a set of input parse
   results from runs of both versions of the grammar over the same
   profile(s).

6) Provided the above requirements are all met gDelta should hopefully
   be able to called from the command line. See the USAGE section for
   details.


REQUIREMENTS

gDelta requires Python 2.7 or greater and the jinja2 templating
language package. To install:

$ pip install Jinja2

The scipy Python module is desirable as clustering is much faster with
this installed, but there is a slower fallback if it is not available.

The HTML output of gDelta can involve a lot of data for large
profiles, thus an up to date modern browser is recommended. Chrome and
Firefox have both been tested and can be recommended. Absolutely zero
testing had been done on Internet Explorer. If you experience problems
with large tables hanging the browser, the only solution at this point
is to use a faster machine. Or wait until someone improves gDelta to
use a saner way of storing data.


USAGE

$ gdelta.py [options] grammar_name grammarA grammarB profile

Where 'grammar_name' is the name that TSDB uses to refer to the
grammar (eg 'erg' or 'gg'), 'grammarA' and 'grammarB' are the labels
corresponding to the relevant grammar entries in the etc/registry file
and 'profile' is either a single TSDB profile name or the name of a
virtual profile. Currently virtual profiles must be located within a
'virtual' directory located within the TSDB database directory. gDelta
also supports reading gold profiles; see the --gold option for
details.

Use the '-h' or '--help' option to find out about the various command
line options.

The output of gDelta is a series of HTML files which can be viewed in
a browser offline and independently of the original script. By default
these files are put in a folder called 'gdelta_out' in the same
directory the script was called from. The best place to start is with
the file suffixed with 'summary.html'. Each page has a help tab in the
top right corner to provide an explanation of the contents.
