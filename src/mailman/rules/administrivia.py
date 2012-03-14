# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""The administrivia rule."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Administrivia',
    ]


from email.iterators import typed_subpart_iterator
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.rules import IRule


# The list of email commands we search for in the Subject header and payload.
# We probably should get this information from the actual implemented
# commands.
EMAIL_COMMANDS = {
    # keyword: (minimum #args, maximum #args)
    'confirm':     (1, 1),
    'help':        (0, 0),
    'info':        (0, 0),
    'lists':       (0, 0),
    'options':     (0, 0),
    'password':    (2, 2),
    'remove':      (0, 0),
    'set':         (3, 3),
    'subscribe':   (0, 3),
    'unsubscribe': (0, 1),
    'who':         (0, 2),
    }



class Administrivia:
    """The administrivia rule."""
    implements(IRule)

    name = 'administrivia'
    description = _('Catch mis-addressed email commands.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        # The list must have the administrivia check enabled.
        if not mlist.administrivia:
            return False
        # First check the Subject text.
        lines_to_check = []
        subject = str(msg.get('subject', ''))
        if subject <> '':
            lines_to_check.append(subject)
        # Search only the first text/plain subpart of the message.  There's
        # really no good way to find email commands in any other content type.
        for part in typed_subpart_iterator(msg, 'text', 'plain'):
            payload = part.get_payload(decode=True)
            lines = payload.splitlines()
            # Count lines without using enumerate() because blank lines in the
            # payload don't count against the maximum examined.
            lineno = 0
            for line in lines:
                line = line.strip()
                if len(line) == 0:
                    continue
                lineno += 1
                if lineno > config.mailman.email_commands_max_lines:
                    break
                lines_to_check.append(line)
            # Only look at the first text/plain part.
            break
        # For each line we're checking, split the line into words.  Then see
        # if it looks like a command with the min-to-max number of arguments.
        for line in lines_to_check:
            words = [word.lower() for word in line.split()]
            if words[0] not in EMAIL_COMMANDS:
                # This is not an administrivia command.
                continue
            minargs, maxargs = EMAIL_COMMANDS[words[0]]
            if minargs <= len(words) - 1 <= maxargs:
                return True
        return False
