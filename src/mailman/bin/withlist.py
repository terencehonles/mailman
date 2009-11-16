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

import os
import sys
import optparse

from zope.component import getUtility

from mailman import interact
from mailman.config import config
from mailman.core.i18n import _
from mailman.core.initialize import initialize
from mailman.interfaces.listmanager import IListManager
from mailman.version import MAILMAN_VERSION


LAST_MLIST  = None
VERBOSE     = True



def do_list(listname, args, func):
    global LAST_MLIST

    if '@' not in listname:
        listname += '@' + config.DEFAULT_EMAIL_HOST

    # XXX FIXME Remove this when this script is converted to
    # MultipleMailingListOptions.
    listname = listname.decode(sys.getdefaultencoding())
    mlist = getUtility(IListManager).get(listname)
    if mlist is None:
        print >> sys.stderr, _('Unknown list: $listname')
    else:
        if VERBOSE:
            print >> sys.stderr, _('Loaded list: $listname')
        LAST_MLIST = mlist
    # Try to import the module and run the callable.
    if func:
        return func(mlist, *args)
    return None



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] listname [args ...]

General framework for interacting with a mailing list object.

There are two ways to use this script: interactively or programmatically.
Using it interactively allows you to play with, examine and modify a
IMailinglist object from Python's interactive interpreter.  When running
interactively, a IMailingList object called 'm' will be available in the
global namespace.

Programmatically, you can write a function to operate on a IMailingList
object, and this script will take care of the housekeeping (see below for
examples).  In that case, the general usage syntax is:

    % bin/withlist [options] listname [args ...]

Here's an example of how to use the -r option.  Say you have a file in the
Mailman installation directory called 'listaddr.py', with the following
two functions:

    def listaddr(mlist):
        print mlist.posting_address

    def requestaddr(mlist):
        print mlist.request_address

Now, from the command line you can print the list's posting address by running
the following from the command line:

    % bin/withlist -r listaddr mylist
    Loading list: mylist
    Importing listaddr ...
    Running listaddr.listaddr() ...
    mylist@myhost.com

And you can print the list's request address by running:

    % bin/withlist -r listaddr.requestaddr mylist
    Loading list: mylist
    Importing listaddr ...
    Running listaddr.requestaddr() ...
    mylist-request@myhost.com

As another example, say you wanted to change the password for a particular
user on a particular list.  You could put the following function in a file
called 'changepw.py':

    from mailman.errors import NotAMemberError

    def changepw(mlist, addr, newpasswd):
        try:
            mlist.setMemberPassword(addr, newpasswd)
            mlist.Save()
        except NotAMemberError:
            print 'No address matched:', addr

and run this from the command line:

    % bin/withlist -l -r changepw mylist somebody@somewhere.org foobar"""))
    parser.add_option('-i', '--interactive',
                      default=None, action='store_true', help=_("""\
Leaves you at an interactive prompt after all other processing is complete.
This is the default unless the -r option is given."""))
    parser.add_option('-r', '--run',
                      type='string', help=_("""\
This can be used to run a script with the opened IMailingList object.  This
works by attempting to import'module' (which must be in the directory
containing withlist, or already be accessible on your sys.path), and then
calling 'callable' from the module.  callable can be a class or function; it
is called with the IMailingList object as the first argument.  If additional
args are given on the command line, they are passed as subsequent positional
args to the callable.

Note that 'module.' is optional; if it is omitted then a module with the name
'callable' will be imported.

The global variable 'r' will be set to the results of this call."""))
    parser.add_option('-a', '--all',
                      default=False, action='store_true', help=_("""\
This option only works with the -r option.  Use this if you want to execute
the script on all mailing lists.  When you use -a you should not include a
listname argument on the command line.  The variable 'r' will be a list of all
the results."""))
    parser.add_option('-q', '--quiet',
                      default=False, action='store_true',
                      help=_('Suppress all status messages.'))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    return parser, opts, args



def main():
    global VERBOSE

    parser, opts, args = parseargs()
    config_file = (os.getenv('MAILMAN_CONFIG_FILE')
                   if opts.config is None
                   else opts.config)
    initialize(config_file, not opts.quiet)

    VERBOSE = not opts.quiet
    # The default for interact is true unless -r was given
    if opts.interactive is None:
        if not opts.run:
            opts.interactive = True
        else:
            opts.interactive = False

    dolist = True
    if len(args) < 1 and not opts.all:
        warning = _('No list name supplied.')
        if opts.interactive:
            # Let them keep going
            print >> sys.stderr, warning
            dolist = False
        else:
            parser.error(warning)

    if opts.all and not opts.run:
        parser.error(_('--all requires --run'))

    # Try to import the module for the callable
    func = None
    if opts.run:
        i = opts.run.rfind('.')
        if i < 0:
            module = opts.run
            callable = opts.run
        else:
            module = opts.run[:i]
            callable = opts.run[i+1:]
        if VERBOSE:
            print >> sys.stderr, _('Importing $module ...')
        __import__(module)
        mod = sys.modules[module]
        if VERBOSE:
            print >> sys.stderr, _('Running ${module}.${callable}() ...')
        func = getattr(mod, callable)

    r = None
    if opts.all:
        r = [do_list(listname, args, func)
             for listname in getUtility(IListManager).names]
    elif dolist:
        listname = args.pop(0).lower().strip()
        r = do_list(listname, args, func)

    # Now go to interactive mode, perhaps
    if opts.interactive:
        if dolist:
            banner = _(
                "The variable 'm' is the $listname mailing list")
        else:
            banner = interact.DEFAULT_BANNER
        overrides = dict(m=LAST_MLIST, r=r,
                         commit=config.db.commit,
                         abort=config.db.abort,
                         config=config)
        interact.interact(upframe=False, banner=banner, overrides=overrides)
