# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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
from mailman.email.validate import validate
from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomainManager)
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.member import MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.modules import call_name


log = logging.getLogger('mailman.error')



def create_list(fqdn_listname, owners=None):
    """Create the named list and apply styles."""
    if owners is None:
        owners = []
    validate(fqdn_listname)
    # pylint: disable-msg=W0612
    listname, domain = fqdn_listname.split('@', 1)
    if domain not in IDomainManager(config):
        raise BadDomainSpecificationError(domain)
    mlist = getUtility(IListManager).create(fqdn_listname)
    for style in config.style_manager.lookup(mlist):
        style.apply(mlist)
    # Coordinate with the MTA, as defined in the configuration file.
    call_name(config.mta.incoming).create(mlist)
    # Create any owners that don't yet exist, and subscribe all addresses as
    # owners of the mailing list.
    user_manager = getUtility(IUserManager)
    for owner_address in owners:
        addr = user_manager.get_address(owner_address)
        if addr is None:
            # XXX Make this use an IRegistrar instead, but that requires
            # sussing out the IDomain stuff.  For now, fake it.
            user = user_manager.create_user(owner_address)
            addr = list(user.addresses)[0]
        addr.subscribe(mlist, MemberRole.owner)
    return mlist



def remove_list(fqdn_listname, mailing_list=None, archives=True):
    """Remove the list and all associated artifacts and subscriptions."""
    removeables = []
    # mailing_list will be None when only residual archives are being removed.
    if mailing_list:
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
    if archives:
        private_dir = config.PRIVATE_ARCHIVE_FILE_DIR
        public_dir  = config.PUBLIC_ARCHIVE_FILE_DIR
        removeables.extend([
            os.path.join(private_dir, fqdn_listname),
            os.path.join(private_dir, fqdn_listname + '.mbox'),
            os.path.join(public_dir, fqdn_listname),
            os.path.join(public_dir, fqdn_listname + '.mbox'),
            ])
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
