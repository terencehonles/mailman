# Copyright (C) 2010 by the Free Software Foundation, Inc.
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

"""REST for mailing lists."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AList',
    'AllLists',
    'ListConfiguration',
    ]


from lazr.config import as_boolean
from restish import http, resource
from zope.component import getUtility

from mailman.app.lifecycle import create_list, remove_list
from mailman.config import config
from mailman.interfaces.domain import BadDomainSpecificationError
from mailman.interfaces.listmanager import (
    IListManager, ListAlreadyExistsError)
from mailman.interfaces.mailinglist import IAcceptableAliasSet
from mailman.interfaces.member import MemberRole
from mailman.rest.helpers import (
    CollectionMixin, PATCH, Validator, etag, no_content, path_to,
    restish_matcher)
from mailman.rest.members import AMember, MembersOfList



@restish_matcher
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
    # XXX 2010-02-25 barry Matchers are undocumented in restish; they return a
    # 3-tuple of (match_args, match_kws, segments).
    return (), dict(role=role, address=segments[1]), ()


@restish_matcher
def roster_matcher(request, segments):
    """A matcher of all members URLs inside mailing lists.

    e.g. /roster/members
         /roster/owners
         /roster/moderators

    The URL roles are the plural form of the MemberRole enum, because the
    former reads better.
    """
    if len(segments) != 2 or segments[0] != 'roster':
        return None
    role = segments[1][:-1]
    try:
        return (), dict(role=MemberRole[role]), ()
    except ValueError:
        # Not a valid role.
        return None


@restish_matcher
def config_matcher(request, segments):
    """A matcher for a mailing list's configuration resource.

    e.g. /config
    """
    if len(segments) == 1 and segments[0] == 'config':
        return (), {}, ()
    # It's something else.
    return None


@restish_matcher
def subresource_config_matcher(request, segments):
    """A matcher for configuration sub-resources.

    e.g. /config/acceptable_aliases
    """
    if len(segments) != 2 or segments[0] != 'config':
        return None
    # Don't check here whether it's a known subresource or not.  Let that be
    # done in subresource_config() method below.
    return (), dict(attribute=segments[1]), ()



class _ListBase(resource.Resource, CollectionMixin):
    """Shared base class for mailing list representations."""

    def _resource_as_dict(self, mlist):
        """See `CollectionMixin`."""
        return dict(
            fqdn_listname=mlist.fqdn_listname,
            host_name=mlist.host_name,
            list_name=mlist.list_name,
            real_name=mlist.real_name,
            self_link=path_to('lists/{0}'.format(mlist.fqdn_listname)),
            )

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(IListManager))


class AList(_ListBase):
    """A mailing list."""

    def __init__(self, list_name):
        self._mlist = getUtility(IListManager).get(list_name)

    @resource.GET()
    def mailing_list(self, request):
        """Return a single mailing list end-point."""
        if self._mlist is None:
            return http.not_found()
        return http.ok([], self._resource_as_json(self._mlist))

    @resource.DELETE()
    def delete_list(self, request):
        """Delete the named mailing list."""
        if self._mlist is None:
            return http.not_found()
        remove_list(self._mlist.fqdn_listname, self._mlist,
                    # XXX 2010-07-06 barry we need a way to remove the list
                    # archives either with the mailing list or afterward.
                    archives=False)
        return no_content()

    @resource.child(member_matcher)
    def member(self, request, segments, role, address):
        """Return a single member representation."""
        return AMember(self._mlist, role, address)

    @resource.child(roster_matcher)
    def roster(self, request, segments, role):
        """Return the collection of all a mailing list's members."""
        return MembersOfList(self._mlist, role)

    @resource.child(config_matcher)
    def config(self, request, segments):
        """Return a mailing list configuration object."""
        return ListConfiguration(self._mlist)

    @resource.child(subresource_config_matcher)
    def subresource_config(self, request, segments, attribute):
        """Return the subresource configuration object.

        This will return a Bad Request if it isn't a known subresource.
        """
        missing = object()
        subresource_class = SUBRESOURCES.get(attribute, missing)
        if subresource_class is missing:
            return http.bad_request(
                [], 'Unknown attribute {0}'.format(attribute))
        return subresource_class(self._mlist, attribute)



class AllLists(_ListBase):
    """The mailing lists."""

    @resource.POST()
    def create(self, request):
        """Create a new mailing list."""
        try:
            validator = Validator(fqdn_listname=unicode)
            mlist = create_list(**validator(request))
        except ListAlreadyExistsError:
            return http.bad_request([], b'Mailing list exists')
        except BadDomainSpecificationError as error:
            return http.bad_request([], b'Domain does not exist {0}'.format(
                error.domain))
        except ValueError as error:
            return http.bad_request([], str(error))
        # wsgiref wants headers to be bytes, not unicodes.
        location = path_to('lists/{0}'.format(mlist.fqdn_listname))
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def collection(self, request):
        """/lists"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))



# The set of readable IMailingList attributes.
READABLE = (
    # Identity.
    'created_at',
    'list_name',
    'host_name',
    'fqdn_listname',
    'real_name',
    'list_id',
    'include_list_post_header',
    'include_rfc2369_headers',
    'advertised',
    'anonymous_list',
    # Contact addresses.
    'posting_address',
    'no_reply_address',
    'owner_address',
    'request_address',
    'bounces_address',
    'join_address',
    'leave_address',
    # Posting history.
    'last_post_at',
    'post_id',
    # Digests.
    'digest_last_sent_at',
    'volume',
    'next_digest_number',
    'digest_size_threshold',
    # Web access.
    'scheme',
    'web_host',
    # Notifications.
    'admin_immed_notify',
    'admin_notify_mchanges',
    # Processing.
    'pipeline',
    'administrivia',
    'filter_content',
    'convert_html_to_plaintext',
    'collapse_alternatives',
    )


def pipeline_validator(pipeline_name):
    """Convert the pipeline name to a string, but only if it's known."""
    if pipeline_name in config.pipelines:
        return unicode(pipeline_name)
    raise ValueError('Unknown pipeline: {0}'.format(pipeline_name))


VALIDATORS = {
    # Identity.
    'real_name': unicode,
    'include_list_post_header': as_boolean,
    'include_rfc2369_headers': as_boolean,
    'advertised': as_boolean,
    'anonymous_list': as_boolean,
    # Digests.
    'digest_size_threshold': float,
    # Notifications.
    'admin_immed_notify': as_boolean,
    'admin_notify_mchanges': as_boolean,
    # Processing.
    'pipeline': pipeline_validator,
    'administrivia': as_boolean,
    'filter_content': as_boolean,
    'convert_html_to_plaintext': as_boolean,
    'collapse_alternatives': as_boolean,
    }


class ListConfiguration(resource.Resource):
    """A mailing list configuration resource."""

    def __init__(self, mailing_list):
        self._mlist = mailing_list

    @resource.GET()
    def get_configuration(self, request):
        """Return a mailing list's readable configuration."""
        resource = {}
        for attribute in READABLE:
            resource[attribute] = getattr(self._mlist, attribute)
        return http.ok([], etag(resource))

    @resource.PUT()
    def put_configuration(self, request):
        """Set all of a mailing list's configuration."""
        # Use PATCH to change just one or a few of the attributes.
        validator = Validator(**VALIDATORS)
        try:
            for key, value in validator(request).items():
                setattr(self._mlist, key, value)
        except ValueError as error:
            return http.bad_request([], str(error))
        return http.ok([], '')

    @PATCH()
    def patch_configuration(self, request):
        """Set a subset of the mailing list's configuration."""
        validator = Validator(_optional=VALIDATORS.keys(), **VALIDATORS)
        try:
            for key, value in validator(request).items():
                setattr(self._mlist, key, value)
        except ValueError as error:
            return http.bad_request([], str(error))
        return http.ok([], '')



class AcceptableAliases(resource.Resource):
    """Resource for the acceptable aliases of a mailing list."""

    def __init__(self, mailing_list, attribute):
        assert attribute == 'acceptable_aliases', (
            'unexpected attribute: {0}'.format(attribute))
        self._mlist = mailing_list

    @resource.GET()
    def aliases(self, request):
        """Return the mailing list's acceptable aliases."""
        aliases = IAcceptableAliasSet(self._mlist)
        resource = dict(aliases=sorted(aliases.aliases))
        return http.ok([], etag(resource))

    @resource.PUT()
    def put_configuration(self, request):
        """Change the acceptable aliases.

        Because this is a PUT operation, all previous aliases are cleared
        first.  Thus, this is an overwrite.  The keys in the request are
        ignored.
        """
        aliases = IAcceptableAliasSet(self._mlist)
        aliases.clear()
        for alias in request.POST.values():
            aliases.add(unicode(alias))
        return http.ok([], '')



SUBRESOURCES = dict(
    acceptable_aliases=AcceptableAliases,
    )
