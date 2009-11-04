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

"""Mailman errors."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AlreadyReceivingDigests',
    'AlreadyReceivingRegularDeliveries',
    'BadPasswordSchemeError',
    'CantDigestError',
    'DiscardMessage',
    'EmailAddressError',
    'HandlerError',
    'HoldMessage',
    'HostileSubscriptionError',
    'InvalidEmailAddress',
    'LostHeldMessage',
    'MailmanError',
    'MailmanException',
    'MemberError',
    'MembershipIsBanned',
    'MustDigestError',
    'NotAMemberError',
    'PasswordError',
    'RejectMessage',
    'SubscriptionError',
    ]



# Base class for all exceptions raised in Mailman.
class MailmanException(Exception):
    pass



# "New" style membership exceptions (new w/ MM2.1)
class MemberError(MailmanException): pass
class NotAMemberError(MemberError): pass
class AlreadyReceivingDigests(MemberError): pass
class AlreadyReceivingRegularDeliveries(MemberError): pass
class CantDigestError(MemberError): pass
class MustDigestError(MemberError): pass
class MembershipIsBanned(MemberError): pass



# New style class based exceptions.  All the above errors should eventually be
# converted.

class MailmanError(MailmanException):
    """Base class for all Mailman errors."""
    pass



# Exception hierarchy for bad email address errors that can be raised from
# mailman.email.validate.validate()
class EmailAddressError(MailmanError):
    """Base class for email address validation errors."""


class InvalidEmailAddress(EmailAddressError):
    """Email address is invalid."""



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
    def __init__(self, notice=None):
        super(RejectMessage, self).__init__()
        if notice is None:
            notice = _('Your message was rejected')
        if notice.endswith('\n\n'):
            pass
        elif notice.endswith('\n'):
            notice += '\n'
        else:
            notice += '\n\n'
        self.notice = notice



# Subscription exceptions
class SubscriptionError(MailmanError):
    """Subscription errors base class."""


class HostileSubscriptionError(SubscriptionError):
    """A cross-subscription attempt was made.

    This exception gets raised when an invitee attempts to use the
    invitation to cross-subscribe to some other mailing list.
    """



class PasswordError(MailmanError):
    """A password related error."""


class BadPasswordSchemeError(PasswordError):
    """A bad password scheme was given."""

    def __init__(self, scheme_name='unknown'):
        super(BadPasswordSchemeError, self).__init__()
        self.scheme_name = scheme_name

    def __str__(self):
        return 'A bad password scheme was given: %s' % self.scheme_name
