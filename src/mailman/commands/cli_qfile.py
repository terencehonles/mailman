# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Getting information out of a qfile."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'QFile',
    ]


import cPickle

from pprint import PrettyPrinter
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.utilities.interact import interact


m = []



class QFile:
    """Get information out of a queue file."""

    implements(ICLISubCommand)

    name = 'qfile'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        self.parser = parser
        command_parser.add_argument(
            '-n', '--noprint',
            dest='doprint', default=True, action='store_false',
            help=_("""\
            Don't attempt to pretty print the object.  This is useful if there
            is some problem with the object and you just want to get an
            unpickled representation.  Useful with 'bin/dumpdb -i <file>'.  In
            that case, the list of unpickled objects will be left in a
            variable called 'm'."""))
        command_parser.add_argument(
            '-i', '--interactive',
            default=False, action='store_true',
            help=_("""\
            Start an interactive Python session, with a variable called 'm'
            containing the list of unpickled objects."""))
        command_parser.add_argument(
            'qfile', metavar='FILENAME', nargs=1,
            help=_('The queue file to dump.'))

    def process(self, args):
        """See `ICLISubCommand`."""
        printer = PrettyPrinter(indent=4)
        assert len(args.qfile) == 1, 'Wrong number of positional arguments'
        with open(args.qfile[0]) as fp:
            while True:
                try:
                    m.append(cPickle.load(fp))
                except EOFError:
                    break
        if args.doprint:
            print _('[----- start pickle -----]')
            for i, obj in enumerate(m):
                count = i + 1
                print _('<----- start object $count ----->')
                if isinstance(obj, basestring):
                    print obj
                else:
                    printer.pprint(obj)
            print _('[----- end pickle -----]')
        count = len(m)
        banner = _("The variable 'm' contains $count objects")
        if args.interactive:
            interact(banner=banner)
