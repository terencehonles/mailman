# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""Common argument parsing."""

__metaclass__ = type
__all__ = [
    'Options',
    'SingleMailingListOptions',
    ]


import sys

from copy import copy
from optparse import Option, OptionParser, OptionValueError

from mailman.config import config
from mailman.core.initialize import initialize
from mailman.i18n import _
from mailman.version import MAILMAN_VERSION



def check_unicode(option, opt, value):
    if isinstance(value, unicode):
        return value
    try:
        return value.decode(sys.getdefaultencoding())
    except UnicodeDecodeError:
        raise OptionValueError(
            'option %s: Cannot decode: %r' % (opt, value))


def check_yesno(option, opt, value):
    value = value.lower()
    if value not in ('yes', 'no', 'y', 'n'):
        raise OptionValueError('option s: invalid: %r' % (opt, value))
    return value[0] == 'y'


class MailmanOption(Option):
    """Extension types for unicode options."""
    TYPES = Option.TYPES + ('unicode', 'yesno')
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER['unicode'] = check_unicode
    TYPE_CHECKER['yesno'] = check_yesno



class Options:
    """Common argument parser."""

    # Subclasses should override.
    usage = None

    def __init__(self):
        self.parser = OptionParser(version=MAILMAN_VERSION,
                                   option_class=MailmanOption,
                                   usage=self.usage)
        self.add_common_options()
        self.add_options()
        options, arguments = self.parser.parse_args()
        self.options = options
        self.arguments = arguments
        # Also, for convenience, place the options in the configuration file
        # because occasional global uses are necessary.
        config.options = self

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

    def initialize(self, propagate_logs=None):
        """Initialize the configuration system.

        After initialization of the configuration system, perform sanity
        checks.  We do it in this order because some sanity checks require the
        configuration to be initialized.

        :param propagate_logs: Optional flag specifying whether log messages
            in sub-loggers should be propagated to the master logger (and
            hence to the root logger).  If not given, propagation is taken
            from the configuration files.
        :type propagate_logs: bool or None.
        """
        initialize(self.options.config, propagate_logs=propagate_logs)
        self.sanity_check()



class SingleMailingListOptions(Options):
    """A helper for specifying the mailing list on the command line."""

    def add_options(self):
        self.parser.add_option(
            '-l', '--listname',
            type='unicode', help=_('The mailing list name'))
        super(SingleMailingListOptions, self).add_options()


class MultipleMailingListOptions(Options):
    """A helper for specifying multiple mailing lists on the command line."""

    def add_options(self):
        self.parser.add_option(
            '-l', '--listname',
            default=[], action='append', dest='listnames', type='unicode',
            help=("""\
A mailing list name.  It is okay to have multiple --listname options."""))

