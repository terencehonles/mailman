# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""Common argument parsing."""

__metaclass__ = type
__all__ = ['Options']


from optparse import OptionParser

from mailman.Version import MAILMAN_VERSION
from mailman.configuration import config
from mailman.i18n import _



class Options:
    """Common argument parser."""

    # Subclasses should override.
    usage = None

    def __init__(self):
        self.parser = OptionParser(version=MAILMAN_VERSION, usage=self.usage)
        self.add_common_options()
        self.add_options()
        options, arguments = self.parser.parse_args()
        self.options = options
        self.arguments = arguments
        # Also, for convenience, place the options in the configuration file
        # because occasional global uses are necessary.
        config.options = self
        self.sanity_check()

    def add_options(self):
        """Allow the subclass to add its own specific arguments."""
        pass

    def sanity_check(self):
        """Allow subclasses to do sanity checking of arguments."""
        pass

    def add_common_options(self):
        """Add options common to all scripts."""
        self.parser.add_option(
            '-C', '--config',
            help=_('Alternative configuration file to use'))
