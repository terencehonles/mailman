# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Implementation of the IUserRegistrar interface."""

__metaclass__ = type
__all__ = [
    'Registrar',
    'adapt_domain_to_registrar',
    ]


import datetime

from pkg_resources import resource_string
from zope.interface import implements

from mailman.Message import UserNotification
from mailman.Utils import ValidateEmail
from mailman.configuration import config
from mailman.i18n import _
from mailman.interfaces import IDomain, IPendable, IRegistrar
from mailman.interfaces.member import MemberRole



class PendableRegistration(dict):
    implements(IPendable)
    PEND_KEY = 'registration'



class Registrar:
    implements(IRegistrar)

    def __init__(self, context):
        self._context = context

    def register(self, address, real_name=None, mlist=None):
        """See `IUserRegistrar`."""
        # First, do validation on the email address.  If the address is
        # invalid, it will raise an exception, otherwise it just returns.
        ValidateEmail(address)
        # Create a pendable for the registration.
        pendable = PendableRegistration(
            type=PendableRegistration.PEND_KEY,
            address=address,
            real_name=real_name)
        if mlist is not None:
            pendable['list_name'] = mlist.fqdn_listname
        token = config.db.pendings.add(pendable)
        # Set up some local variables for translation interpolation.
        domain = IDomain(self._context)
        domain_name = _(domain.email_host)
        contact_address = domain.contact_address
        confirm_url = domain.confirm_url(token)
        confirm_address = domain.confirm_address(token)
        email_address = address
        # Calculate the message's Subject header.  XXX Have to deal with
        # translating this subject header properly.  XXX Must deal with
        # VERP_CONFIRMATIONS as well.
        subject = 'confirm ' + token
        # Send a verification email to the address.
        text = _(resource_string('mailman.templates.en', 'verify.txt'))
        msg = UserNotification(address, confirm_address, subject, text)
        msg.send(mlist=None)
        return token

    def confirm(self, token):
        """See `IUserRegistrar`."""
        # For convenience
        pendable = config.db.pendings.confirm(token)
        if pendable is None:
            return False
        missing = object()
        address = pendable.get('address', missing)
        real_name = pendable.get('real_name', missing)
        list_name = pendable.get('list_name', missing)
        if pendable.get('type') != PendableRegistration.PEND_KEY:
            # It seems like it would be very difficult to accurately guess
            # tokens, or brute force an attack on the SHA1 hash, so we'll just
            # throw the pendable away in that case.  It's possible we'll need
            # to repend the event or adjust the API to handle this case
            # better, but for now, the simpler the better.
            return False
        # We are going to end up with an IAddress for the verified address
        # and an IUser linked to this IAddress.  See if any of these objects
        # currently exist in our database.
        usermgr = config.db.user_manager
        addr = (usermgr.get_address(address)
                if address is not missing else None)
        user = (usermgr.get_user(address)
                if address is not missing else None)
        # If there is neither an address nor a user matching the confirmed
        # record, then create the user, which will in turn create the address
        # and link the two together
        if addr is None:
            assert user is None, 'How did we get a user but not an address?'
            user = usermgr.create_user(address, real_name)
            # Because the database changes haven't been flushed, we can't use
            # IUserManager.get_address() to find the IAddress just created
            # under the hood.  Instead, iterate through the IUser's addresses,
            # of which really there should be only one.
            for addr in user.addresses:
                if addr.address == address:
                    break
            else:
                raise AssertionError('Could not find expected IAddress')
        elif user is None:
            user = usermgr.create_user()
            user.real_name = real_name
            user.link(addr)
        else:
            # The IAddress and linked IUser already exist, so all we need to
            # do is verify the address.
            pass
        addr.verified_on = datetime.datetime.now()
        # If this registration is tied to a mailing list, subscribe the person
        # to the list right now.
        list_name = pendable.get('list_name')
        if list_name is not None:
            mlist = config.db.list_manager.get(list_name)
            if mlist:
                addr.subscribe(mlist, MemberRole.member)
        return True

    def discard(self, token):
        # Throw the record away.
        config.db.pendings.confirm(token)



def adapt_domain_to_registrar(iface, obj):
    """Adapt `IDomain` to `IRegistrar`.

    :param iface: The interface to adapt to.
    :type iface: `zope.interface.Interface`
    :param obj: The object being adapted.
    :type obj: `IDomain`
    :return: An `IRegistrar` instance if adaptation succeeded or None if it
        didn't.
    """
    return (Registrar(obj)
            if IDomain.providedBy(obj) and iface is IRegistrar
            else None)
