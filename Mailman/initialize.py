# Copyright (C) 2006-2007 by the Free Software Foundation, Inc.
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

"""Initialize all global state.

Every entrance into the Mailman system, be it by command line, mail program,
or cgi, must call the initialize function here in order for the system's
global state to be set up properly.  Typically this is called after command
line argument parsing, since some of the initialization behavior is controlled
by the command line arguments.
"""

import os
import sys
import pkg_resources

from zope.interface.verify import verifyObject

import Mailman.configuration
import Mailman.loginit

from Mailman.app.plugins import get_plugin
from Mailman.interfaces import IDatabase



# These initialization calls are separated for the testing framework, which
# needs to do some internal calculations after config file loading and log
# initialization, but before database initialization.  Generally all other
# code will just call initialize().

def initialize_1(config_path, propagate_logs):
    # By default, set the umask so that only owner and group can read and
    # write our files.  Specifically we must have g+rw and we probably want
    # o-rwx although I think in most cases it doesn't hurt if other can read
    # or write the files.  Note that the Pipermail archive has more
    # restrictive permissions in order to handle private archives, but it
    # handles that correctly.
    os.umask(007)
    Mailman.configuration.config.load(config_path)
    # Create the queue and log directories if they don't already exist.
    Mailman.configuration.config.ensure_directories_exist()
    Mailman.loginit.initialize(propagate_logs)


def initialize_2(debug=False):
    database_plugin = get_plugin('mailman.database')
    # Instantiate the database plugin, ensure that it's of the right type, and
    # initialize it.  Then stash the object on our configuration object.
    database = database_plugin()
    verifyObject(IDatabase, database)
    database.initialize(debug)
    Mailman.configuration.config.db = database


def initialize(config_path=None, propagate_logs=False):
    initialize_1(config_path, propagate_logs)
    initialize_2()
