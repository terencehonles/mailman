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
    'AdminWebServiceApplication',
    'AdminWebServiceRequest',
    'make_server',
    ]


import logging

# Don't use wsgiref.simple_server.make_server() because we need to override
# BaseHTTPRequestHandler.log_message() so that logging output will go to the
# proper Mailman logger instead of stderr, as is the default.
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

from lazr.restful import register_versioned_request_utility
from lazr.restful.interfaces import (
    IServiceRootResource, IWebServiceClientRequest)
from lazr.restful.simple import Request, RootResource
from lazr.restful.wsgi import WSGIApplication
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.publish import publish

from mailman.config import config
from mailman.core.system import system
from mailman.interfaces.domain import IDomain, IDomainCollection
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.mailinglist import IMailingList
from mailman.interfaces.member import IMember
from mailman.interfaces.membership import ISubscriptionService
from mailman.interfaces.rest import IResolvePathNames
from mailman.rest.publication import AdminWebServicePublication

log = logging.getLogger('mailman.http')



# Marker interfaces for multiversion lazr.restful.
class I30Version(IWebServiceClientRequest):
    pass


class IDevVersion(IWebServiceClientRequest):
    pass



class AdminWebServiceRootResource(RootResource):
    """The lazr.restful non-versioned root resource."""

    implements(IResolvePathNames)

    def __init__(self):
        # We can't build these mappings at construction time.
        self._collections = None
        self._entry_links = None
        self._top_names = None

    def _build_top_level_objects(self):
        """See `RootResource`."""
        self._collections = dict(
            domains=(IDomain, getUtility(IDomainCollection)),
            lists=(IMailingList, getUtility(IListManager)),
            members=(IMember, getUtility(ISubscriptionService)),
            )
        self._entry_links = dict(
            system=system,
            )
        self._top_names = self._collection.copy()
        self._top_names.update(self._entry_links)
        return (self._collections, self._entry_links)

    def get(self, name):
        """See `IResolvePathNames`."""
        top_names = dict(
            domains=getUtility(IDomainCollection),
            lists=getUtility(IListManager),
            members=getUtility(ISubscriptionService),
            system=system,
            )
        return top_names.get(name)


class AdminWebServiceApplication(WSGIApplication):
    """A WSGI application for the admin REST interface."""

    # The only thing we need to override is the publication class.
    publication_class = AdminWebServicePublication


class AdminWebServiceWSGIRequestHandler(WSGIRequestHandler):
    """Handler class which just logs output to the right place."""

    def log_message(self, format, *args):
        """See `BaseHTTPRequestHandler`."""
        log.info('%s - - %s', self.address_string(), format % args)



def make_server():
    """Create the WSGI admin REST server."""
    register_versioned_request_utility(I30Version, '3.0')
    register_versioned_request_utility(IDevVersion, 'dev')
    host = config.webservice.hostname
    port = int(config.webservice.port)
    server = WSGIServer((host, port), AdminWebServiceWSGIRequestHandler)
    server.set_app(AdminWebServiceApplication)
    return server
