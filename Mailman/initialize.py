# Copyright (C) 2006 by the Free Software Foundation, Inc.
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

import Mailman.configuration
import Mailman.database
import Mailman.loginit



def initialize(config=None, propagate_logs=False):
    Mailman.configuration.config.load(config)
    Mailman.loginit.initialize(propagate_logs)
    Mailman.database.initialize()
