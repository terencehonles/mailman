# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
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

"""Initialize all global state.

Every entrance into the Mailman system, be it by command line, mail program,
or cgi, must call the initialize function here in order for the system's
global state to be set up properly.  Typically this is called after command
line argument parsing, since some of the initialization behavior is controlled
by the command line arguments.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'initialize',
    'initialize_1',
    'initialize_2',
    'initialize_3',
    ]


import os
import sys

from pkg_resources import resource_string
from zope.configuration import xmlconfig
from zope.interface.verify import verifyObject

import mailman.config.config
import mailman.core.logging

from mailman.interfaces.database import IDatabase
from mailman.utilities.modules import call_name



# These initialization calls are separated for the testing framework, which
# needs to do some internal calculations after config file loading and log
# initialization, but before database initialization.  Generally all other
# code will just call initialize().

def initialize_1(config_path=None, propagate_logs=None):
    """First initialization step.

    * The configuration system
    * Run-time directories
    * The logging subsystem
    * Internationalization

    :param config_path: The path to the configuration file.
    :type config_path: string
    :param propagate_logs: Should the log output propagate to stderr?
    :type propagate_logs: boolean or None
    """
    # By default, set the umask so that only owner and group can read and
    # write our files.  Specifically we must have g+rw and we probably want
    # o-rwx although I think in most cases it doesn't hurt if other can read
    # or write the files.  Note that the Pipermail archive has more
    # restrictive permissions in order to handle private archives, but it
    # handles that correctly.
    os.umask(007)
    mailman.config.config.load(config_path)
    # Create the queue and log directories if they don't already exist.
    mailman.config.config.ensure_directories_exist()
    mailman.core.logging.initialize(propagate_logs)


def initialize_2(debug=False):
    """Second initialization step.

    * Pre-hook
    * Rules
    * Chains
    * Pipelines
    * Commands

    :param debug: Should the database layer be put in debug mode?
    :type debug: boolean
    """
    # Run the pre-hook if there is one.
    config = mailman.config.config
    if config.mailman.pre_hook:
        call_name(config.mailman.pre_hook)
    # Instantiate the database class, ensure that it's of the right type, and
    # initialize it.  Then stash the object on our configuration object.
    database_class = config.database['class']
    database = call_name(database_class)
    verifyObject(IDatabase, database)
    database.initialize(debug)
    config.db = database
    # Initialize the rules and chains.  Do the imports here so as to avoid
    # circular imports.
    from mailman.app.commands import initialize as initialize_commands
    from mailman.core.chains import initialize as initialize_chains
    from mailman.core.pipelines import initialize as initialize_pipelines
    from mailman.core.rules import initialize as initialize_rules
    # Order here is somewhat important.
    initialize_rules()
    initialize_chains()
    initialize_pipelines()
    initialize_commands()


def initialize_3():
    """Third initialization step.

    * Zope component architecture
    * Post-hook
    """
    zcml = resource_string('mailman.config', 'configure.zcml')
    xmlconfig.string(zcml)
    # Run the post-hook if there is one.
    config = mailman.config.config
    if config.mailman.post_hook:
        call_name(config.mailman.post_hook)



def initialize(config_path=None, propagate_logs=None):
    initialize_1(config_path, propagate_logs)
    initialize_2()
    initialize_3()
