# Copyright (C) 2002-2012 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, print_function, unicode_literals

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
from mailman.interfaces.member import DeliveryMode, MemberRole
from mailman.interfaces.registrar import IRegistrar
from mailman.interfaces.subscriptions import ISubscriptionService
from mailman.interfaces.usermanager import IUserManager



class Join:
    """The email 'join' command."""

    implements(IEmailCommand)

    name = 'join'
    # XXX 2012-02-29 BAW: DeliveryMode.summary is not yet supported.
    argument_description = '[digest=<no|mime|plain>]'
    description = _("""\
You will be asked to confirm your subscription request and you may be issued a
provisional password.

By using the 'digest' option, you can specify whether you want digest delivery
or not.  If not specified, the mailing list's default delivery mode will be
used.
""")
    short_description = _('Join this mailing list.')

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        # Parse the arguments.
        delivery_mode = self._parse_arguments(arguments, results)
        if delivery_mode is ContinueProcessing.no:
            return ContinueProcessing.no
        display_name, address = parseaddr(msg['from'])
        # Address could be None or the empty string.
        if not address:
            address = msg.sender
        if not address:
            print(_('$self.name: No valid address found to subscribe'),
                  file=results)
            return ContinueProcessing.no
        # Have we already seen one join request from this user during the
        # processing of this email?
        joins = getattr(results, 'joins', set())
        if address in joins:
            # Do not register this join.
            return ContinueProcessing.yes
        joins.add(address)
        results.joins = joins
        person = formataddr((display_name, address))
        # Is this person already a member of the list?  Search for all
        # matching memberships.
        members = getUtility(ISubscriptionService).find_members(
            address, mlist.fqdn_listname, MemberRole.member)
        if len(members) > 0:
            print(_('$person is already a member'), file=results)
        else:
            getUtility(IRegistrar).register(mlist, address, 
                                            display_name, delivery_mode)
            print(_('Confirmation email sent to $person'), file=results)
        return ContinueProcessing.yes

    def _parse_arguments(self, arguments, results):
        """Parse command arguments.

        :param arguments: The sequences of arguments as given to the
            `process()` method.
        :param results: The results object.
        :return: The delivery mode, None, or ContinueProcessing.no on error.
        """
        mode = DeliveryMode.regular
        for argument in arguments:
            parts = argument.split('=', 1)
            if len(parts) != 2 or parts[0] != 'digest':
                print(self.name, _('bad argument: $argument'),
                      file=results)
                return ContinueProcessing.no
            mode = {
                'no': DeliveryMode.regular,
                'plain': DeliveryMode.plaintext_digests,
                'mime': DeliveryMode.mime_digests,
                }.get(parts[1])
            if mode is None:
                print(self.name, _('bad argument: $argument'),
                      file=results)
                return ContinueProcessing.no
        return mode



class Subscribe(Join):
    """The email 'subscribe' command (an alias for 'join')."""

    name = 'subscribe'
    description = _("An alias for 'join'.")
    short_description = description



class Leave:
    """The email 'leave' command."""

    implements(IEmailCommand)

    name = 'leave'
    argument_description = ''
    description = _("""Leave this mailing list.  

You may be asked to confirm your request.""")
    short_description = _('Leave this mailing list.')

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        email = msg.sender
        if not email:
            print(_('$self.name: No valid email address found to unsubscribe'),
                  file=results)
            return ContinueProcessing.no
        user_manager = getUtility(IUserManager)
        user = user_manager.get_user(email)
        if user is None:
            print(_('No registered user for email address: $email'),
                  file=results)
            return ContinueProcessing.no
        # The address that the -leave command was sent from, must be verified.
        # Otherwise you could link a bogus address to anyone's account, and
        # then send a leave command from that address.
        if user_manager.get_address(email).verified_on is None:
            print(_('Invalid or unverified email address: $email'),
                  file=results)
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
            print(_(
                '$self.name: $email is not a member of $mlist.fqdn_listname'),
                file=results)
            return ContinueProcessing.no
        member.unsubscribe()
        person = formataddr((user.display_name, email))
        print(_('$person left $mlist.fqdn_listname'), file=results)
        return ContinueProcessing.yes


class Unsubscribe(Leave):
    """The email 'unsubscribe' command (an alias for 'leave')."""

    name = 'unsubscribe'
    description = _("An alias for 'leave'.")
    short_description = description
