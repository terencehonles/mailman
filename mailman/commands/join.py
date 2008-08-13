# Copyright (C) 2002-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""The email commands 'join' and 'subscribe'."""

__metaclass__ = type
__all__ = [
    'Join',
    'Subscribe',
    ]


from email.header import decode_header, make_header
from email.utils import parseaddr
from zope.interface import implements

from mailman.Utils import MakeRandomPassword
from mailman.app.membership import confirm_add_member
from mailman.configuration import config
from mailman.i18n import _
from mailman.interfaces import (
    ContinueProcessing, DeliveryMode, IEmailCommand)



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
        address, delivery_mmode = self._parser_arguments(mlist, arguments)
        if address is None:
            realname, address = parseaddr(msg['from'])
        # Address could be None or the empty string.
        if not address:
            address = msg.get_sender()
        if not address:
            print >> results, self.name, \
                  _('No valid address found to subscribe')
            return ContinueProcessing.no
        password = MakeRandomPassword()
        try:
            confirm_add_member(mlist, address, realname, password,
                               delivery_mode, mlist.preferred_language)
        except XXX:
            pass
        print >> results, self.name, address, \
              (_('digest delivery') if digest else _('regular delivery'))
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


    # Fill in empty defaults
    if digest is None:
        digest = mlist.digest_is_default
    if password is None:
        password = Utils.MakeRandomPassword()
    if address is None:
        realname, address = parseaddr(res.msg['from'])
        if not address:
            # Fall back to the sender address
            address = res.msg.get_sender()
        if not address:
            res.results.append(_('No valid address found to subscribe'))
            return STOP
        # Watch for encoded names
        try:
            h = make_header(decode_header(realname))
            # BAW: in Python 2.2, use just unicode(h)
            realname = h.__unicode__()
        except UnicodeError:
            realname = u''
        # Coerce to byte string if uh contains only ascii
        try:
            realname = realname.encode('us-ascii')
        except UnicodeError:
            pass
    # Create the UserDesc record and do a non-approved subscription
    listowner = mlist.GetOwnerEmail()
    userdesc = UserDesc(address, realname, password, digest)
    remote = res.msg.get_sender()
    try:
        mlist.AddMember(userdesc, remote)
    except Errors.MembershipIsBanned:
        res.results.append(_("""\
The email address you supplied is banned from this mailing list.
If you think this restriction is erroneous, please contact the list
owners at %(listowner)s."""))
        return STOP
    except Errors.InvalidEmailAddress:
        res.results.append(_("""\
Mailman won't accept the given email address as a valid address."""))
        return STOP
    except Errors.MMAlreadyAMember:
        res.results.append(_('You are already subscribed!'))
        return STOP
    except Errors.MMCantDigestError:
        res.results.append(
            _('No one can subscribe to the digest of this list!'))
        return STOP
    except Errors.MMMustDigestError:
        res.results.append(_('This list only supports digest subscriptions!'))
        return STOP
    except Errors.MMSubscribeNeedsConfirmation:
        # We don't need to respond /and/ send a confirmation message.
        res.respond = 0
    except Errors.MMNeedApproval:
        res.results.append(_("""\
Your subscription request has been forwarded to the list administrator
at %(listowner)s for review."""))
    else:
        # Everything is a-ok
        res.results.append(_('Subscription request succeeded.'))
