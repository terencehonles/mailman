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

"""Print the Mailman version."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'main',
    ]


# pylint: disable-msg=W0611
from mailman.core.system import system
from mailman.i18n import _
from mailman.options import Options



class ScriptOptions(Options):
    """See `Options`."""
    usage = _("""\
%prog

Print the Mailman version and exit.""")



def main():
    """Main entry point."""
    options = ScriptOptions()
    options.initialize()
    print _('Using $system.mailman_version')
