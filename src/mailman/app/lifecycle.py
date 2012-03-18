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

"""Application level list creation."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'create_list',
    'remove_list',
    ]


import os
import shutil
import logging

from zope.component import getUtility

from mailman.config import config
from mailman.interfaces.address import IEmailValidator
from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomainManager)
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.member import MemberRole
from mailman.interfaces.styles import IStyleManager
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.modules import call_name


log = logging.getLogger('mailman.error')



def create_list(fqdn_listname, owners=None):
    """Create the named list and apply styles.

    The mailing may not exist yet, but the domain specified in `fqdn_listname`
    must exist.

    :param fqdn_listname: The fully qualified name for the new mailing list.
    :type fqdn_listname: string
    :param owners: The mailing list owners.
    :type owners: list of string email addresses
    :return: The new mailing list.
    :rtype: `IMailingList`
    :raises BadDomainSpecificationError: when the hostname part of
        `fqdn_listname` does not exist.
    :raises ListAlreadyExistsError: when the mailing list already exists.
    :raises InvalidEmailAddressError: when the fqdn email address is invalid.
    """
    if owners is None:
        owners = []
    # This raises I
    getUtility(IEmailValidator).validate(fqdn_listname)
    listname, domain = fqdn_listname.split('@', 1)
    if domain not in getUtility(IDomainManager):
        raise BadDomainSpecificationError(domain)
    mlist = getUtility(IListManager).create(fqdn_listname)
    for style in getUtility(IStyleManager).lookup(mlist):
        style.apply(mlist)
    # Coordinate with the MTA, as defined in the configuration file.
    call_name(config.mta.incoming).create(mlist)
    # Create any owners that don't yet exist, and subscribe all addresses as
    # owners of the mailing list.
    user_manager = getUtility(IUserManager)
    for owner_address in owners:
        address = user_manager.get_address(owner_address)
        if address is None:
            user = user_manager.create_user(owner_address)
            address = list(user.addresses)[0]
        mlist.subscribe(address, MemberRole.owner)
    return mlist



def remove_list(fqdn_listname, mailing_list=None):
    """Remove the list and all associated artifacts and subscriptions."""
    removeables = []
    # mailing_list will be None when only residual archives are being removed.
    if mailing_list is not None:
        # Remove all subscriptions, regardless of role.
        for member in mailing_list.subscribers.members:
            member.unsubscribe()
        # Delete the mailing list from the database.
        getUtility(IListManager).delete(mailing_list)
        # Do the MTA-specific list deletion tasks
        call_name(config.mta.incoming).create(mailing_list)
        # Remove the list directory.
        removeables.append(os.path.join(config.LIST_DATA_DIR, fqdn_listname))
    # Remove any stale locks associated with the list.
    for filename in os.listdir(config.LOCK_DIR):
        fn_listname = filename.split('.')[0]
        if fn_listname == fqdn_listname:
            removeables.append(os.path.join(config.LOCK_DIR, filename))
    # Now that we know what files and directories to delete, delete them.
    for target in removeables:
        if not os.path.exists(target):
            pass
        elif os.path.islink(target):
            os.unlink(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        elif os.path.isfile(target):
            os.unlink(target)
        else:
            log.error('Could not delete list artifact: %s', target)
