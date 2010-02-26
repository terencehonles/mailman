# Copyright (C) 2009-2010 by the Free Software Foundation, Inc.
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

"""Module stuff."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import json
import hashlib
import logging

from restish import http, resource
from wsgiref.simple_server import make_server as wsgi_server

from zope.component import getUtility
from zope.interface import implements

from mailman.app.membership import delete_member
from mailman.config import config
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomain, IDomainManager)
from mailman.interfaces.listmanager import (
    IListManager, ListAlreadyExistsError, NoSuchListError)
from mailman.interfaces.mailinglist import IMailingList
from mailman.interfaces.member import (
    AlreadySubscribedError, IMember, MemberRole)
from mailman.interfaces.membership import ISubscriptionService


COMMASPACE = ', '
log = logging.getLogger('mailman.http')



