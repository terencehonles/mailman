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

__metaclass__ = type
__all__ = [
    'create_list',
    'remove_list',
    ]


import os
import sys
import shutil
import logging

from mailman import Utils
from mailman.Utils import ValidateEmail
from mailman.config import config
from mailman.core import errors
from mailman.interfaces.member import MemberRole


log = logging.getLogger('mailman.error')



def create_list(fqdn_listname, owners=None):
    """Create the named list and apply styles."""
    if owners is None:
        owners = []
    ValidateEmail(fqdn_listname)
    listname, domain = Utils.split_listname(fqdn_listname)
    if domain not in config.domains:
        raise errors.BadDomainSpecificationError(domain)
    mlist = config.db.list_manager.create(fqdn_listname)
    for style in config.style_manager.lookup(mlist):
        style.apply(mlist)
    # Coordinate with the MTA, as defined in the configuration file.
    module_name, class_name = config.mta.incoming.rsplit('.', 1)
    __import__(module_name)
    getattr(sys.modules[module_name], class_name)().create(mlist)
    # Create any owners that don't yet exist, and subscribe all addresses as
    # owners of the mailing list.
    usermgr = config.db.user_manager
    for owner_address in owners:
        addr = usermgr.get_address(owner_address)
        if addr is None:
            # XXX Make this use an IRegistrar instead, but that requires
            # sussing out the IDomain stuff.  For now, fake it.
            user = usermgr.create_user(owner_address)
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
        config.db.list_manager.delete(mailing_list)
        # Do the MTA-specific list deletion tasks
        module_name, class_name = config.mta.incoming.rsplit('.', 1)
        __import__(module_name)
        getattr(sys.modules[module_name], class_name)().create(mlist)
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
        if os.path.islink(target):
            os.unlink(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        elif os.path.isfile(target):
            os.unlink(target)
        else:
            log.error('Could not delete list artifact: %s', target)
