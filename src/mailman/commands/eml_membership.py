# Copyright (C) 2002-2011 by the Free Software Foundation, Inc.
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

"""The email commands 'join' and 'subscribe'."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Join',
    'Subscribe',
    'Leave',
    'Unsubscribe',
    ]


from email.utils import formataddr, parseaddr
from zope.component import getUtility
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.command import ContinueProcessing, IEmailCommand
from mailman.interfaces.member import DeliveryMode
from mailman.interfaces.registrar import IRegistrar
from mailman.interfaces.usermanager import IUserManager



class Join:
    """The email 'join' command."""

    implements(IEmailCommand)

    name = 'join'
    argument_description = '[digest=<yes|no>] [address=<address>]'
    description = _("""\
Join this mailing list.  You will be asked to confirm your subscription
request and you may be issued a provisional password.

By using the 'digest' option, you can specify whether you want digest delivery
or not.  If not specified, the mailing list's default will be used.  You can
also subscribe an alternative address by using the 'address' option.  For
example:

    join address=myotheraddress@example.com
""")

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        # Parse the arguments.
        address, delivery_mode = self._parse_arguments(arguments)
        # address could be None or the empty string.
        if not address:
            real_name, address = parseaddr(msg['from'])
        # Address could be None or the empty string.
        if not address:
            address = msg.sender
        if not address:
            print >> results, _(
                '$self.name: No valid address found to subscribe')
            return ContinueProcessing.no
        getUtility(IRegistrar).register(mlist, address, real_name)
        person = formataddr((real_name, address))
        print >> results, _('Confirmation email sent to $person')
        return ContinueProcessing.yes

    def _parse_arguments(self, arguments):
        """Parse command arguments.

        :param arguments: The sequences of arguments as given to the
            `process()` method.
        :return: address, delivery_mode
        """
        address = None
        delivery_mode = None
        for argument in arguments:
            parts = argument.split('=', 1)
            if parts[0].lower() == 'digest':
                if digest is not None:
                    print >> results, self.name, \
                          _('duplicate argument: $argument')
                    return ContinueProcessing.no
                if len(parts) == 0:
                    # We treat just plain 'digest' as 'digest=yes'.  We don't
                    # yet support the other types of digest delivery.
                    delivery_mode = DeliveryMode.mime_digests
                else:
                    if parts[1].lower() == 'yes':
                        delivery_mode = DeliveryMode.mime_digests
                    elif parts[1].lower() == 'no':
                        delivery_mode = DeliveryMode.regular
                    else:
                        print >> results, self.name, \
                              _('bad argument: $argument')
                        return ContinueProcessing.no
            elif parts[0].lower() == 'address':
                if address is not None:
                    print >> results, self.name, \
                          _('duplicate argument $argument')
                    return ContinueProcessing.no
                if len(parts) == 0:
                    print >> results, self.name, \
                          _('missing argument value: $argument')
                    return ContinueProcessing.no
                if len(parts) > 1:
                    print >> results, self.name, \
                          _('too many argument values: $argument')
                    return ContinueProcessing.no
                address = parts[1]
        return address, delivery_mode



class Subscribe(Join):
    """The email 'subscribe' command (an alias for 'join')."""

    name = 'subscribe'



class Leave:
    """The email 'leave' command."""

    implements(IEmailCommand)

    name = 'leave'
    argument_description = ''
    description = _(
        'Leave this mailing list.  You will be asked to confirm your request.')

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        email = msg.sender
        if not email:
            print >> results, _(
                '$self.name: No valid email address found to unsubscribe')
            return ContinueProcessing.no
        user_manager = getUtility(IUserManager)
        user = user_manager.get_user(email)
        if user is None:
            print >> results, _('No registered user for email address: $email')
            return ContinueProcessing.no
        # The address that the -leave command was sent from, must be verified.
        # Otherwise you could link a bogus address to anyone's account, and
        # then send a leave command from that address.
        if user_manager.get_address(email).verified_on is None:
            print >> results, _('Invalid or unverified email address: $email')
            return ContinueProcessing.no
        for user_address in user.addresses:
            # Only recognize verified addresses.
            if user_address.verified_on is None:
                continue
            member = mlist.members.get_member(user_address.email)
            if member is not None:
                break
        else:
            # None of the user's addresses are subscribed to this mailing list.
            print >> results, _(
                '$self.name: $email is not a member of $mlist.fqdn_listname')
            return ContinueProcessing.no
        member.unsubscribe()
        person = formataddr((user.real_name, email))
        print >> results, _('$person left $mlist.fqdn_listname')
        return ContinueProcessing.yes


class Unsubscribe(Leave):
    """The email 'unsubscribe' command (an alias for 'leave')."""

    name = 'unsubscribe'
