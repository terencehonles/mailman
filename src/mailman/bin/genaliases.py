# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

__metaclass__ = type
__all__ = [
    'main',
    ]


import sys

from mailman.config import config
from mailman.core.i18n import _
from mailman.options import Options
from mailman.utilities.modules import call_name



class ScriptOptions(Options):
    """Options for the genaliases script."""

    usage = _("""\
%prog [options]

Regenerate the Mailman specific MTA aliases from scratch.  The actual output
depends on the value of the 'MTA' variable in your etc/mailman.cfg file.""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-q', '--quiet',
            default=False, action='store_true', help=_("""\
Some MTA output can include more verbose help text.  Use this to tone down the
verbosity."""))




def main():
    options = ScriptOptions()
    options.initialize()

    # Get the MTA-specific module.
    call_name(config.mta.incoming).regenerate()



if __name__ == '__main__':
    main()
