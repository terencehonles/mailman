# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""Legacy Mailman exceptions.

This module is largely obsolete, though not all exceptions in use have been
migrated to their proper location.  There are still a number of Mailman 2.1
exceptions floating about in here too.

The right place for exceptions is in the interface module for their related
interfaces.
"""


from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AlreadyReceivingDigests',
    'AlreadyReceivingRegularDeliveries',
    'BadPasswordSchemeError',
    'CantDigestError',
    'DiscardMessage',
    'HandlerError',
    'HoldMessage',
    'LostHeldMessage',
    'MailmanError',
    'MailmanException',
    'MemberError',
    'MustDigestError',
    'PasswordError',
    'RejectMessage',
    ]



# Base class for all exceptions raised in Mailman.
class MailmanException(Exception):
    pass



# "New" style membership exceptions (new w/ MM2.1)
class MemberError(MailmanException): pass
class AlreadyReceivingDigests(MemberError): pass
class AlreadyReceivingRegularDeliveries(MemberError): pass
class CantDigestError(MemberError): pass
class MustDigestError(MemberError): pass



# New style class based exceptions.  All the above errors should eventually be
# converted.

class MailmanError(MailmanException):
    """Base class for all Mailman errors."""
    pass



# Exceptions for admin request database
class LostHeldMessage(MailmanError):
    """Held message was lost."""
    pass



def _(s):
    return s


# Exceptions for the Handler subsystem
class HandlerError(MailmanError):
    """Base class for all handler errors."""


class HoldMessage(HandlerError):
    """Base class for all message-being-held short circuits."""

    # funky spelling is necessary to break import loops
    reason = _('For some unknown reason')

    def reason_notice(self):
        return self.reason

    # funky spelling is necessary to break import loops
    rejection = _('Your message was rejected')

    def rejection_notice(self, mlist):
        return self.rejection


class DiscardMessage(HandlerError):
    """The message can be discarded with no further action"""


class RejectMessage(HandlerError):
    """The message will be bounced back to the sender"""



class PasswordError(MailmanError):
    """A password related error."""


class BadPasswordSchemeError(PasswordError):
    """A bad password scheme was given."""

    def __init__(self, scheme_name='unknown'):
        super(BadPasswordSchemeError, self).__init__()
        self.scheme_name = scheme_name

    def __str__(self):
        return 'A bad password scheme was given: %s' % self.scheme_name
