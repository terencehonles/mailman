# Copyright (C) 2001-2011 by the Free Software Foundation, Inc.
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

"""Recognizes simple heuristically delimited warnings."""

__metaclass__ = type
__all__ = [
    'SimpleWarning',
    ]


from mailman.bouncers.simplematch import _c
from mailman.bouncers.simplematch import SimpleMatch
from mailman.interfaces.bounce import Stop



# This is a list of tuples of the form
#
#     (start cre, end cre, address cre)
#
# where 'cre' means compiled regular expression, start is the line just before
# the bouncing address block, end is the line just after the bouncing address
# block, and address cre is the regexp that will recognize the addresses.  It
# must have a group called 'addr' which will contain exactly and only the
# address that bounced.
PATTERNS = [
    # pop3.pta.lia.net
    (_c('The address to which the message has not yet been delivered is'),
     _c('No action is required on your part'),
     _c(r'\s*(?P<addr>\S+@\S+)\s*')),
    # This is from MessageSwitch.  It is a kludge because the text that
    # identifies it as a warning only comes after the address.  We can't
    # use ecre, because it really isn't significant, so we fake it.  Once
    # we see the start, we know it's a warning, and we're going to return
    # Stop anyway, so we match anything for the address and end.
    (_c('This is just a warning, you do not need to take any action'),
     _c('.+'),
     _c('(?P<addr>.+)')),
    # Symantec_AntiVirus_for_SMTP_Gateways - see comments for MessageSwitch
    (_c('Delivery attempts will continue to be made'),
     _c('.+'),
     _c('(?P<addr>.+)')),
    # googlemail.com warning
    (_c('Delivery to the following recipient has been delayed'),
     _c('.+'),
     _c('\s*(?P<addr>.+)')),
    # Exchange warning message.
    (_c('This is an advisory-only email'),
     _c('has been postponed'),
     _c('"(?P<addr>[^"]+)"')),
    # Next one goes here...
    ]



class SimpleWarning(SimpleMatch):
    """Recognizes simple heuristically delimited warnings."""

    PATTERNS = PATTERNS

    def process(self, msg):
        """See `SimpleMatch`."""
        if super(SimpleWarning, self).process(msg):
            # It's a recognized warning so stop now.
            return Stop
        else:
            return set()
