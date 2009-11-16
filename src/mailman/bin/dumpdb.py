# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

import pprint
import cPickle

from mailman.config import config
from mailman.core.i18n import _
from mailman.interact import interact
from mailman.options import Options


COMMASPACE = ', '
m = []



class ScriptOptions(Options):
    usage=_("""\
%prog [options] filename

Dump the contents of any Mailman queue file.  The queue file is a data file
with multiple Python pickles in it.""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-n', '--noprint',
            dest='doprint', default=True, action='store_false',
            help=_("""\
Don't attempt to pretty print the object.  This is useful if there is some
problem with the object and you just want to get an unpickled representation.
Useful with 'bin/dumpdb -i <file>'.  In that case, the list of
unpickled objects will be left in a variable called 'm'."""))
        self.parser.add_option(
            '-i', '--interact',
            default=False, action='store_true',
            help=_("""\
Start an interactive Python session, with a variable called 'm' containing the
list of unpickled objects."""))

    def sanity_check(self):
        if len(self.arguments) < 1:
            self.parser.error(_('No filename given.'))
        elif len(self.arguments) > 1:
            self.parser.error(_('Unexpected arguments'))
        else:
            self.filename = self.arguments[0]



def main():
    options = ScriptOptions()
    options.initialize()

    pp = pprint.PrettyPrinter(indent=4)
    with open(options.filename) as fp:
        while True:
            try:
                m.append(cPickle.load(fp))
            except EOFError:
                break
    if options.options.doprint:
        print _('[----- start pickle -----]')
        for i, obj in enumerate(m):
            count = i + 1
            print _('<----- start object $count ----->')
            if isinstance(obj, basestring):
                print obj
            else:
                pp.pprint(obj)
        print _('[----- end pickle -----]')
    if options.options.interact:
        interact()
