#! @PYTHON@
#
# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

import sys
import pprint
import cPickle
import marshal
import optparse

from Mailman import Version
from Mailman.configuration import config
from Mailman.i18n import _


COMMASPACE = ', '



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options] filename

Dump the contents of any Mailman `database' file.

If the filename ends with `.db', then it is assumed that the file contains a
Python marshal.  If the file ends with `.pck' then it is assumed to contain a
Python pickle.  In either case, if you want to override the default assumption
-- or if the file ends in neither suffix -- use the -p or -m flags."""))
    parser.add_option('-m', '--marshal',
                      default=False, action='store_true',
                      help=_("""\
Assume the file contains a Python marshal,
overridding any automatic guessing."""))
    parser.add_option('-p', '--pickle',
                      default=False, action='store_true',
                      help=_("""\
Assume the file contains a Python pickle,
overridding any automatic guessing."""))
    parser.add_option('-n', '--noprint',
                      default=False, action='store_true',
                      help=_("""\
Don't attempt to pretty print the object.  This is useful if there's
some problem with the object and you just want to get an unpickled
representation.  Useful with `python -i bin/dumpdb <file>'.  In that
case, the root of the tree will be left in a global called "msg"."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    # Options.
    # None == guess, 0 == pickle, 1 == marshal
    opts.filetype = None
    if opts.pickle:
        opts.filetype = 0
    if opts.marshal:
        opts.filetype = 1
    opts.doprint = not opts.noprint
    if len(args) < 1:
        parser.error(_('No filename given.'))
    elif len(args) > 1:
        pargs = COMMASPACE.join(args)
        parser.error(_('Bad arguments: $pargs'))
    else:
        opts.filename = args[0]
    if opts.filetype is None:
        if opts.filename.endswith('.db'):
            opts.filetype = 1
        elif opts.filename.endswith('.pck'):
            opts.filetype = 0
        else:
            parser.error(_('Please specify either -p or -m.'))
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)

    # Handle dbs
    pp = pprint.PrettyPrinter(indent=4)
    if opts.filetype == 1:
        load = marshal.load
        typename = 'marshal'
    else:
        load = cPickle.load
        typename = 'pickle'
    fp = open(opts.filename)
    m = []
    try:
        cnt = 1
        if opts.doprint:
            print _('[----- start $typename file -----]')
        while True:
            try:
                obj = load(fp)
            except EOFError:
                if opts.doprint:
                    print _('[----- end $typename file -----]')
                break
            if opts.doprint:
                print _('<----- start object $cnt ----->')
                if isinstance(obj, str):
                    print obj
                else:
                    pp.pprint(obj)
            cnt += 1
            m.append(obj)
    finally:
        fp.close()
