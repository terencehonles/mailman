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


import json
import hashlib
import logging

from restish.app import RestishApp
from restish import http, resource
from wsgiref.simple_server import (
    make_server as wsgi_server, WSGIRequestHandler)

from zope.component import getUtility
from zope.interface import implements

from mailman.app.membership import delete_member
from mailman.config import config
from mailman.core.system import system
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomain, IDomainManager)
from mailman.interfaces.listmanager import (
    IListManager, ListAlreadyExistsError, NoSuchListError)
from mailman.interfaces.mailinglist import IMailingList
from mailman.interfaces.member import (
    AlreadySubscribedError, IMember, MemberRole)
from mailman.interfaces.membership import ISubscriptionService
from mailman.interfaces.rest import APIValueError, IResolvePathNames
#from mailman.rest.publication import AdminWebServicePublication


COMMASPACE = ', '
log = logging.getLogger('mailman.http')



class Root(resource.Resource):
    """The RESTful root resource."""

    @resource.child('3.0')
    def api_version(self, request, segments):
        return TopLevel()


class TopLevel(resource.Resource):
    """Top level collections and entries."""

    @resource.child()
    def system(self, request, segments):
        response = dict(
            mailman_version=system.mailman_version,
            python_version=system.python_version,
            resource_type_link='http://localhost:8001/3.0/#system',
            self_link='http://localhost:8001/3.0/system',
            )
        etag = hashlib.sha1(repr(response)).hexdigest()
        response['http_etag'] = '"{0}"'.format(etag)
        return http.ok([], json.dumps(response))

    @resource.child()
    def domains(self, request, segments):
        if len(segments) == 0:
            return AllDomains()
        elif len(segments) == 1:
            return ADomain(segments[0]), []
        else:
            return http.bad_request()

    @resource.child()
    def lists(self, request, segments):
        if len(segments) == 0:
            return AllLists()
        else:
            list_name = segments.pop(0)
            return AList(list_name), segments

    @resource.child()
    def members(self, request, segments):
        if len(segments) == 0:
            return AllMembers()
        return http.bad_request()



class _DomainBase(resource.Resource):
    """Shared base class for domain representations."""

    def _format_domain(self, domain):
        """Format the data for a single domain."""
        domain_data = dict(
            base_url=domain.base_url,
            contact_address=domain.contact_address,
            description=domain.description,
            email_host=domain.email_host,
            resource_type_link='http://localhost:8001/3.0/#domain',
            self_link='http://localhost:8001/3.0/domains/{0}'.format(
                domain.email_host),
            url_host=domain.url_host,
            )
        etag = hashlib.sha1(repr(domain_data)).hexdigest()
        domain_data['http_etag'] = '"{0}"'.format(etag)
        return domain_data


class ADomain(_DomainBase):
    """A domain."""

    def __init__(self, domain):
        self._domain = domain

    @resource.GET()
    def domain(self, request):
        """Return a single domain end-point."""
        domain = getUtility(IDomainManager).get(self._domain)
        if domain is None:
            return http.not_found()
        return http.ok([], json.dumps(self._format_domain(domain)))


class AllDomains(_DomainBase):
    """The domains."""

    @resource.POST()
    def create(self, request):
        """Create a new domain."""
        # XXX 2010-02-23 barry Sanity check the POST arguments by
        # introspection of the target method, or via descriptors.
        domain_manager = getUtility(IDomainManager)
        try:
            # webob gives this to us as a string, but we need unicodes.
            kws = dict((key, unicode(value))
                       for key, value in request.POST.items())
            domain = domain_manager.add(**kws)
        except BadDomainSpecificationError:
            return http.bad_request([], 'Domain exists')
        # wsgiref wants headers to be bytes, not unicodes.
        location = b'http://localhost:8001/3.0/domains/{0}'.format(
            domain.email_host)
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def container(self, request):
        """Return the /domains end-point."""
        domains = list(getUtility(IDomainManager))
        if len(domains) == 0:
            return http.ok(
                [], json.dumps(dict(resource_type_link=
                                    'http://localhost:8001/3.0/#domains',
                                    start=None,
                                    total_size=0)))
        entries = []
        response = dict(
            resource_type_link='http://localhost:8001/3.0/#domains',
            start=0,
            total_size=len(domains),
            entries=entries,
            )
        for domain in domains:
            domain_data = self._format_domain(domain)
            entries.append(domain_data)
        return http.ok([], json.dumps(response))



class _ListBase(resource.Resource):
    """Shared base class for mailing list representations."""

    def _format_list(self, mlist):
        """Format the mailing list for a single domain."""
        list_data = dict(
            fqdn_listname=mlist.fqdn_listname,
            host_name=mlist.host_name,
            list_name=mlist.list_name,
            real_name=mlist.real_name,
            resource_type_link='http://localhost:8001/3.0/#list',
            self_link='http://localhost:8001/3.0/lists/{0}'.format(
                mlist.fqdn_listname),
            )
        etag = hashlib.sha1(repr(list_data)).hexdigest()
        list_data['http_etag'] = '"{0}"'.format(etag)
        return list_data


def member_matcher(request, segments):
    """A matcher of member URLs inside mailing lists.

    e.g. /member/aperson@example.org
    """
    if len(segments) != 2:
        return None
    try:
        role = MemberRole[segments[0]]
    except ValueError:
        # Not a valid role.
        return None
    # No more segments.
    return (), dict(role=role, address=segments[1]), ()

# XXX 2010-02-24 barry Seems like contrary to the documentation, matchers
# cannot be plain function, because matchers must have a .score attribute.
# OTOH, I think they support regexps, so that might be a better way to go.
member_matcher.score = ()


class AList(_ListBase):
    """A mailing list."""

    def __init__(self, list_name):
        self._mlist = getUtility(IListManager).get(list_name)

    @resource.GET()
    def mailing_list(self, request):
        """Return a single mailing list end-point."""
        if self._mlist is None:
            return http.not_found()
        return http.ok([], json.dumps(self._format_list(self._mlist)))

    @resource.child(member_matcher)
    def member(self, request, segments, role, address):
        return AMember(self._mlist, role, address)


class AllLists(_ListBase):
    """The mailing lists."""

    @resource.POST()
    def create(self, request):
        """Create a new mailing list."""
        # XXX 2010-02-23 barry Sanity check the POST arguments by
        # introspection of the target method, or via descriptors.
        list_manager = getUtility(IListManager)
        try:
            # webob gives this to us as a string, but we need unicodes.
            kws = dict((key, unicode(value))
                       for key, value in request.POST.items())
            mlist = list_manager.new(**kws)
        except ListAlreadyExistsError:
            return http.bad_request([], b'Mailing list exists')
        except BadDomainSpecificationError as error:
            return http.bad_request([], b'Domain does not exist {0}'.format(
                error.domain))
        # wsgiref wants headers to be bytes, not unicodes.
        location = b'http://localhost:8001/3.0/lists/{0}'.format(
            mlist.fqdn_listname)
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def container(self, request):
        """Return the /lists end-point."""
        mlists = list(getUtility(IListManager))
        if len(mlists) == 0:
            return http.ok(
                [], json.dumps(dict(resource_type_link=
                                    'http://localhost:8001/3.0/#lists',
                                    start=None,
                                    total_size=0)))
        entries = []
        response = dict(
            resource_type_link='http://localhost:8001/3.0/#lists',
            start=0,
            total_size=len(mlists),
            entries=entries,
            )
        for mlist in mlists:
            list_data = self._format_list(mlist)
            entries.append(list_data)
        return http.ok([], json.dumps(response))



class _MemberBase(resource.Resource):
    """Shared base class for member representations."""

    def _format_member(self, member):
        """Format the data for a single member."""
        enum, dot, role = str(member.role).partition('.')
        member_data = dict(
            resource_type_link='http://localhost:8001/3.0/#member',
            self_link='http://localhost:8001/3.0/lists/{0}/{1}/{2}'.format(
                member.mailing_list, role, member.address.address),
            )
        etag = hashlib.sha1(repr(member_data)).hexdigest()
        member_data['http_etag'] = '"{0}"'.format(etag)
        return member_data


class AMember(_MemberBase):
    """A member."""

    def __init__(self, mailing_list, role, address):
        self._mlist = mailing_list
        self._role = role
        self._address = address
        # XXX 2010-02-24 barry There should be a more direct way to get a
        # member out of a mailing list.
        if self._role is MemberRole.member:
            roster = self._mlist.members
        elif self._role is MemberRole.owner:
            roster = self._mlist.owners
        elif self._role is MemberRole.moderator:
            roster = self._mlist.moderators
        else:
            raise AssertionError(
                'Undefined MemberRole: {0}'.format(self._role))
        self._member = roster.get_member(self._address)

    @resource.GET()
    def member(self, request):
        """Return a single member end-point."""
        return http.ok([], json.dumps(self._format_member(self._member)))

    @resource.DELETE()
    def delete(self, request):
        """Delete the member (i.e. unsubscribe)."""
        # Leaving a list is a bit different than deleting a moderator or
        # owner.  Handle the former case first.  For now too, we will not send
        # an admin or user notification.
        if self._role is MemberRole.member:
            delete_member(self._mlist, self._address, False, False)
        else:
            self._member.unsubscribe()
        return http.ok([], '')


class AllMembers(_MemberBase):
    """The members."""

    @resource.POST()
    def create(self, request):
        """Create a new member."""
        # XXX 2010-02-23 barry Sanity check the POST arguments by
        # introspection of the target method, or via descriptors.
        service = getUtility(ISubscriptionService)
        try:
            # webob gives this to us as a string, but we need unicodes.
            kws = dict((key, unicode(value))
                       for key, value in request.POST.items())
            member = service.join(**kws)
        except AlreadySubscribedError:
            return http.bad_request([], b'Member already subscribed')
        except NoSuchListError:
            return http.bad_request([], b'No such list')
        except InvalidEmailAddressError:
            return http.bad_request([], b'Invalid email address')
        except APIValueError as error:
            return http.bad_request([], str(error))
        # wsgiref wants headers to be bytes, not unicodes.
        location = b'http://localhost:8001/3.0/lists/{0}/member/{1}'.format(
            member.mailing_list, member.address.address)
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def container(self, request):
        """Return the /members end-point."""
        members = list(getUtility(ISubscriptionService))
        if len(members) == 0:
            return http.ok(
                [], json.dumps(dict(resource_type_link=
                                    'http://localhost:8001/3.0/#members',
                                    start=None,
                                    total_size=0)))
        entries = []
        response = dict(
            resource_type_link='http://localhost:8001/3.0/#members',
            start=0,
            total_size=len(members),
            entries=entries,
            )
        for member in members:
            member_data = self._format_member(member)
            entries.append(member_data)
        return http.ok([], json.dumps(response))




## class AdminWebServiceRootResource(RootResource):
##     """The lazr.restful non-versioned root resource."""

##     implements(IResolvePathNames)

##     # XXX 2010-02-16 barry lazr.restful really wants this class to exist and
##     # be a subclass of RootResource.  Our own traversal really wants this to
##     # implement IResolvePathNames.  RootResource says to override
##     # _build_top_level_objects() to return the top-level objects, but that
##     # appears to never be called by lazr.restful, so you've got me.  I don't
##     # understand this, which sucks, so just ensure that it doesn't do anything
##     # useful so if/when I do understand this, I can resolve the conflict
##     # between the way lazr.restful wants us to do things and the way our
##     # traversal wants to do things.
##     def _build_top_level_objects(self):
##         """See `RootResource`."""
##         raise NotImplementedError('Magic suddenly got invoked')

##     def get(self, name):
##         """See `IResolvePathNames`."""
##         top_names = dict(
##             domains=getUtility(IDomainCollection),
##             lists=getUtility(IListManager),
##             members=getUtility(ISubscriptionService),
##             system=system,
##             )
##         return top_names.get(name)


## class AdminWebServiceApplication(WSGIApplication):
##     """A WSGI application for the admin REST interface."""

##     # The only thing we need to override is the publication class.
##     publication_class = AdminWebServicePublication


class AdminWebServiceWSGIRequestHandler(WSGIRequestHandler):
    """Handler class which just logs output to the right place."""

    def log_message(self, format, *args):
        """See `BaseHTTPRequestHandler`."""
        log.info('%s - - %s', self.address_string(), format % args)


class AdminWebServiceApplication(RestishApp):
    """Interpose in the restish request processor."""

    def __call__(self, environ, start_response):
        """See `RestishApp`."""
        try:
            response = super(AdminWebServiceApplication, self).__call__(
                environ, start_response)
        except:
            config.db.abort()
            raise
        else:
            config.db.commit()
            return response



def make_server():
    """Create the WSGI admin REST server."""
    app = AdminWebServiceApplication(Root())
    host = config.webservice.hostname
    port = int(config.webservice.port)
    server = wsgi_server(
        host, port, app,
        handler_class=AdminWebServiceWSGIRequestHandler)
    return server
