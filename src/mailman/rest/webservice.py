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
#
# XXX 2010-02-16 barry Gah!  lazr.restful's multiversion.txt document says
# these classes should get generated, and the registrations should happen,
# automatically.  This is not the case AFAICT.  Why?!

class I30Version(IWebServiceClientRequest):
    pass


class IDevVersion(IWebServiceClientRequest):
    pass



class AdminWebServiceRootResource(RootResource):
    """The lazr.restful non-versioned root resource."""

    implements(IResolvePathNames)

    # XXX 2010-02-16 barry lazr.restful really wants this class to exist and
    # be a subclass of RootResource.  Our own traversal really wants this to
    # implement IResolvePathNames.  RootResource says to override
    # _build_top_level_objects() to return the top-level objects, but that
    # appears to never be called by lazr.restful, so you've got me.  I don't
    # understand this, which sucks, so just ensure that it doesn't do anything
    # useful so if/when I do understand this, I can resolve the conflict
    # between the way lazr.restful wants us to do things and the way our
    # traversal wants to do things.
    def _build_top_level_objects(self):
        """See `RootResource`."""
        raise NotImplementedError('Magic suddenly got invoked')

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
    # XXX 2010-02-16 barry Gah!  lazr.restful's multiversion.txt document says
    # these classes should get generated, and the registrations should happen,
    # automatically.  This is not the case AFAICT.  Why?!
    register_versioned_request_utility(I30Version, '3.0')
    register_versioned_request_utility(IDevVersion, 'dev')
    host = config.webservice.hostname
    port = int(config.webservice.port)
    server = WSGIServer((host, port), AdminWebServiceWSGIRequestHandler)
    server.set_app(AdminWebServiceApplication)
    return server
