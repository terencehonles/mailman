# Copyright (C) 2002-2009 by the Free Software Foundation, Inc.
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



def main():
    options = Options()
    options.initialize()

    switchboard = config.switchboards['shunt']
    switchboard.recover_backup_files()

    for filebase in switchboard.files:
        try:
            msg, msgdata = switchboard.dequeue(filebase)
            whichq = msgdata.get('whichq', 'in')
            config.switchboards[whichq].enqueue(msg, msgdata)
        except Exception, e:
            # If there are any unshunting errors, log them and continue trying
            # other shunted messages.
            print >> sys.stderr, _(
                'Cannot unshunt message $filebase, skipping:\n$e')
        else:
            # Unlink the .bak file left by dequeue()
            switchboard.finish(filebase)
