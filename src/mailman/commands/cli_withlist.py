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

"""bin/mailman withlist"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Shell',
    'Withlist',
    ]


import re
import sys

from lazr.config import as_boolean
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.listmanager import IListManager
from mailman.utilities.interact import DEFAULT_BANNER, interact
from mailman.utilities.modules import call_name

# Global holding onto the open mailing list.
m = None
# Global holding the results of --run.
r = None



class Withlist:
    """Operate on a mailing list.

    For detailed help, see --details
    """

    implements(ICLISubCommand)

    name = 'withlist'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        self.parser = parser
        command_parser.add_argument(
            '-i', '--interactive',
            default=None, action='store_true', help=_("""\
            Leaves you at an interactive prompt after all other processing is
            complete.  This is the default unless the --run option is
            given."""))
        command_parser.add_argument(
            '-r', '--run',
            help=_("""\
            Run a script on a mailing list.  The argument is the module path
            to a callable.  This callable will be imported and then called
            with the mailing list as the first argument.  If additional
            arguments are given at the end of the command line, they are
            passed as subsequent positional arguments to the callable.  For
            additional help, see --details.
            """))
        command_parser.add_argument(
            '--details',
            default=False, action='store_true',
            help=_('Print detailed instructions on using this command.'))
        # Optional positional argument.
        command_parser.add_argument(
            'listname', metavar='LISTNAME', nargs='?',
            help=_("""\
            The 'fully qualified list name', i.e. the posting address of the
            mailing list to inject the message into.  This can be a Python
            regular expression, in which case all mailing lists whose posting
            address matches will be processed.  To use a regular expression,
            LISTNAME must start with a ^ (and the matching is done with
            re.match().  LISTNAME cannot be a regular expression unless --run
            is given."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        global m, r
        banner = DEFAULT_BANNER
        # Detailed help wanted?
        if args.details:
            self._details()
            return
        # Interactive is the default unless --run was given.
        if args.interactive is None:
            interactive = (args.run is None)
        else:
            interactive = args.interactive
        # List name cannot be a regular expression if --run is not given.
        if args.listname and args.listname.startswith('^') and not args.run:
            self.parser.error(_('Regular expression requires --run'))
            return
        # Handle --run.
        list_manager = getUtility(IListManager)
        if args.run:
            # When the module and the callable have the same name, a shorthand
            # without the dot is allowed.
            dotted_name = (args.run if '.' in args.run
                           else '{0}.{0}'.format(args.run))
            if args.listname is None:
                self.parser.error(_('--run requires a mailing list name'))
                return
            elif args.listname.startswith('^'):
                r = {}
                cre = re.compile(args.listname, re.IGNORECASE)
                for mailing_list in list_manager.mailing_lists:
                    if cre.match(mailing_list.fqdn_listname):
                        results = call_name(dotted_name, mailing_list)
                        r[mailing_list.fqdn_listname] = results
            else:
                fqdn_listname = args.listname
                m = list_manager.get(fqdn_listname)
                if m is None:
                    self.parser.error(_('No such list: $fqdn_listname'))
                    return
                r = call_name(dotted_name, m)
        else:
            # Not --run.
            if args.listname is not None:
                fqdn_listname = args.listname
                m = list_manager.get(fqdn_listname)
                if m is None:
                    self.parser.error(_('No such list: $fqdn_listname'))
                    return
                banner = _(
                    "The variable 'm' is the $fqdn_listname mailing list")
        # All other processing is finished; maybe go into interactive mode.
        if interactive:
            overrides = dict(
                m=m,
                commit=config.db.commit,
                abort=config.db.abort,
                config=config,
                )
            banner = config.shell.banner + '\n' + banner
            if as_boolean(config.shell.use_ipython):
                self._start_ipython(overrides, banner)
            else:
                self._start_python(overrides, banner)

    def _start_ipython(self, overrides, banner):
        try:
            from IPython.frontend.terminal.embed import InteractiveShellEmbed
            ipshell = InteractiveShellEmbed(banner1=banner, user_ns=overrides)
            ipshell()
        except ImportError:
            print _('ipython is not available, set use_ipython to no')

    def _start_python(self, overrides, banner):
        # Set the tab completion.
        try:
            import readline, rlcompleter
            readline.parse_and_bind('tab: complete')
        except ImportError:
            pass
        else:
            sys.ps1 = config.shell.prompt + ' '
        interact(upframe=False, banner=banner, overrides=overrides)

    def _details(self):
        """Print detailed usage."""
        # Split this up into paragraphs for easier translation.
        print _("""\
This script provides you with a general framework for interacting with a
mailing list.""")
        print
        print _("""\
There are two ways to use this script: interactively or programmatically.
Using it interactively allows you to play with, examine and modify a mailing
list from Python's interactive interpreter.  When running interactively, the
variable 'm' will be available in the global namespace.  It will reference the
mailing list object.""")
        print
        print _("""\
Programmatically, you can write a function to operate on a mailing list, and
this script will take care of the housekeeping (see below for examples).  In
that case, the general usage syntax is:

    % bin/mailman withlist [options] listname [args ...]""")
        print
        print _("""\
Here's an example of how to use the --run option.  Say you have a file in the
Mailman installation directory called 'listaddr.py', with the following two
functions:

    def listaddr(mlist):
        print mlist.posting_address

    def requestaddr(mlist):
        print mlist.request_address""")
        print
        print _("""\
You can print the list's posting address by running the following from the
command line:

    % bin/mailman withlist -r listaddr mylist@example.com
    Importing listaddr ...
    Running listaddr.listaddr() ...
    mylist@example.com""")
        print
        print _("""\
And you can print the list's request address by running:

    % bin/mailman withlist -r listaddr.requestaddr mylist
    Importing listaddr ...
    Running listaddr.requestaddr() ...
    mylist-request@example.com""")
        print
        print _("""\
As another example, say you wanted to change the display name for a particular
mailing list.  You could put the following function in a file called
'change.pw':

    def change(mlist, display_name):
        mlist.display_name = display_name
        # Required to save changes to the database.
        commit()

and run this from the command line:

    % bin/mailman withlist -r change mylist@example.com 'My List'""")



class Shell(Withlist):
    """An alias for `withlist`."""

    name = 'shell'
