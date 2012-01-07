# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Options',
    'SingleMailingListOptions',
    'MultipleMailingListOptions',
    ]


import os
import sys

from copy import copy
from optparse import Option, OptionParser, OptionValueError

from mailman.config import config
from mailman.core.i18n import _
from mailman.core.initialize import initialize
from mailman.version import MAILMAN_VERSION



def check_unicode(option, opt, value):
    """Check that the value is a unicode string."""
    if isinstance(value, unicode):
        return value
    try:
        return value.decode(sys.getdefaultencoding())
    except UnicodeDecodeError:
        raise OptionValueError(
            'option {0}: Cannot decode: {1}'.format(opt, value))


def check_yesno(option, opt, value):
    """Check that the value is 'yes' or 'no'."""
    value = value.lower()
    if value not in ('yes', 'no', 'y', 'n'):
        raise OptionValueError('option {0}: invalid: {1}'.format(opt, value))
    return value[0] == 'y'


class MailmanOption(Option):
    """Extension types for unicode options."""
    TYPES = Option.TYPES + ('unicode', 'yesno')
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER['unicode'] = check_unicode
    TYPE_CHECKER['yesno'] = check_yesno


class SafeOptionParser(OptionParser):
    """A unicode-compatible `OptionParser`.

    Python's standard option parser does not accept unicode options.  Rather
    than try to fix that, this class wraps the add_option() method and saves
    having to wrap the options in str() calls.
    """
    def add_option(self, *args, **kwargs):
        """See `OptionParser`."""
        # Check to see if the first or first two options are unicodes and turn
        # them into 8-bit strings before calling the superclass's method.
        if len(args) == 0:
            return OptionParser.add_option(self, *args, **kwargs)
        old_args = list(args)
        new_args = []
        arg0 = old_args.pop(0)
        new_args.append(str(arg0))
        if len(old_args) > 0:
            arg1 = old_args.pop(0)
            new_args.append(str(arg1))
        new_args.extend(old_args)
        return OptionParser.add_option(self, *new_args, **kwargs)



class Options:
    """Common argument parser."""

    # Subclasses should override.
    usage = None

    def __init__(self):
        self.parser = SafeOptionParser(
            version=MAILMAN_VERSION,
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
        # Python requires str types here.
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
        # Fall back to using the environment variable if -C is not given.
        config_file = (os.getenv('MAILMAN_CONFIG_FILE')
                       if self.options.config is None
                       else self.options.config)
        initialize(config_file, propagate_logs=propagate_logs)
        self.sanity_check()



class SingleMailingListOptions(Options):
    """A helper for specifying the mailing list on the command line."""

    def add_options(self):
        """See `Options`."""
        self.parser.add_option(
            '-l', '--listname',
            type='unicode', help=_('The mailing list name'))
        super(SingleMailingListOptions, self).add_options()


class MultipleMailingListOptions(Options):
    """A helper for specifying multiple mailing lists on the command line."""

    def add_options(self):
        """See `Options`."""
        self.parser.add_option(
            '-l', '--listname',
            default=[], action='append', dest='listnames', type='unicode',
            help=_("""\
A mailing list name.  It is okay to have multiple --listname options."""))
