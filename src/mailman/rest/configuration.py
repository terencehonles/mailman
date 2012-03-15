# Copyright (C) 2010-2012 by the Free Software Foundation, Inc.
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

"""Mailing list configuration via REST API."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ListConfiguration',
    ]


from lazr.config import as_boolean, as_timedelta
from restish import http, resource

from mailman.config import config
from mailman.interfaces.action import Action
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.mailinglist import IAcceptableAliasSet, ReplyToMunging
from mailman.rest.helpers import PATCH, etag, no_content
from mailman.rest.validator import Validator, enum_validator



class GetterSetter:
    """Get and set attributes on mailing lists.

    Most attributes are fairly simple - a getattr() or setattr() on the
    mailing list does the trick, with the appropriate encoding or decoding on
    the way in and out.  Encoding doesn't happen here though; the standard
    JSON library handles most types, but see ExtendedEncoder in
    mailman.rest.helpers for additional support.

    Others are more complicated since they aren't kept in the model as direct
    columns in the database.  These will use subclasses of this base class.
    Read-only attributes will have a decoder which always raises ValueError.
    """

    def __init__(self, decoder=None):
        """Create a getter/setter for a specific list attribute.

        :param decoder: The callable for decoding a web request value string
            into the specific data type needed by the `IMailingList`
            attribute.  Use None to indicate a read-only attribute.  The
            callable should raise ValueError when the web request value cannot
            be converted.
        :type decoder: callable
        """
        self.decoder = decoder

    def get(self, mlist, attribute):
        """Return the named mailing list attribute value.

        :param mlist: The mailing list.
        :type mlist: `IMailingList`
        :param attribute: The attribute name.
        :type attribute: string
        :return: The attribute value, ready for JSON encoding.
        :rtype: object
        """
        return getattr(mlist, attribute)

    def put(self, mlist, attribute, value):
        """Set the named mailing list attribute value.

        :param mlist: The mailing list.
        :type mlist: `IMailingList`
        :param attribute: The attribute name.
        :type attribute: string
        :param value: The new value for the attribute.
        :type request_value: object
        """
        setattr(mlist, attribute, value)

    def __call__(self, value):
        """Convert the value to its internal format.

        :param value: The web request value to convert.
        :type value: string
        :return: The converted value.
        :rtype: object
        """
        if self.decoder is None:
            return value
        return self.decoder(value)


class AcceptableAliases(GetterSetter):
    """Resource for the acceptable aliases of a mailing list."""

    def get(self, mlist, attribute):
        """Return the mailing list's acceptable aliases."""
        assert attribute == 'acceptable_aliases', (
            'Unexpected attribute: {0}'.format(attribute))
        aliases = IAcceptableAliasSet(mlist)
        return sorted(aliases.aliases)

    def put(self, mlist, attribute, value):
        """Change the acceptable aliases.

        Because this is a PUT operation, all previous aliases are cleared
        first.  Thus, this is an overwrite.  The keys in the request are
        ignored.
        """
        assert attribute == 'acceptable_aliases', (
            'Unexpected attribute: {0}'.format(attribute))
        alias_set = IAcceptableAliasSet(mlist)
        alias_set.clear()
        for alias in value:
            alias_set.add(unicode(alias))



# Additional validators for converting from web request strings to internal
# data types.  See below for details.

def pipeline_validator(pipeline_name):
    """Convert the pipeline name to a string, but only if it's known."""
    if pipeline_name in config.pipelines:
        return unicode(pipeline_name)
    raise ValueError('Unknown pipeline: {0}'.format(pipeline_name))


def list_of_unicode(values):
    """Turn a list of things into a list of unicodes."""
    return [unicode(value) for value in values]



# This is the list of IMailingList attributes that are exposed through the
# REST API.  The values of the keys are the GetterSetter instance holding the
# decoder used to convert the web request string to an internally valid value.
# The instance also contains the get() and put() methods used to retrieve and
# set the attribute values.  Its .decoder attribute will be None for read-only
# attributes.
#
# The decoder must either return the internal value or raise a ValueError if
# the conversion failed (e.g. trying to turn 'Nope' into a boolean).
#
# Many internal value types can be automatically JSON encoded, but see
# mailman.rest.helpers.ExtendedEncoder for specializations of certain types
# (e.g. datetimes, timedeltas, enums).

ATTRIBUTES = dict(
    acceptable_aliases=AcceptableAliases(list_of_unicode),
    admin_immed_notify=GetterSetter(as_boolean),
    admin_notify_mchanges=GetterSetter(as_boolean),
    administrivia=GetterSetter(as_boolean),
    advertised=GetterSetter(as_boolean),
    anonymous_list=GetterSetter(as_boolean),
    autorespond_owner=GetterSetter(enum_validator(ResponseAction)),
    autorespond_postings=GetterSetter(enum_validator(ResponseAction)),
    autorespond_requests=GetterSetter(enum_validator(ResponseAction)),
    autoresponse_grace_period=GetterSetter(as_timedelta),
    autoresponse_owner_text=GetterSetter(unicode),
    autoresponse_postings_text=GetterSetter(unicode),
    autoresponse_request_text=GetterSetter(unicode),
    bounces_address=GetterSetter(None),
    collapse_alternatives=GetterSetter(as_boolean),
    convert_html_to_plaintext=GetterSetter(as_boolean),
    created_at=GetterSetter(None),
    default_member_action=GetterSetter(enum_validator(Action)),
    default_nonmember_action=GetterSetter(enum_validator(Action)),
    description=GetterSetter(unicode),
    digest_last_sent_at=GetterSetter(None),
    digest_size_threshold=GetterSetter(float),
    filter_content=GetterSetter(as_boolean),
    fqdn_listname=GetterSetter(None),
    generic_nonmember_action=GetterSetter(int),
    mail_host=GetterSetter(None),
    include_list_post_header=GetterSetter(as_boolean),
    include_rfc2369_headers=GetterSetter(as_boolean),
    join_address=GetterSetter(None),
    last_post_at=GetterSetter(None),
    leave_address=GetterSetter(None),
    list_name=GetterSetter(None),
    next_digest_number=GetterSetter(None),
    no_reply_address=GetterSetter(None),
    owner_address=GetterSetter(None),
    post_id=GetterSetter(None),
    posting_address=GetterSetter(None),
    posting_pipeline=GetterSetter(pipeline_validator),
    display_name=GetterSetter(unicode),
    reply_goes_to_list=GetterSetter(enum_validator(ReplyToMunging)),
    request_address=GetterSetter(None),
    scheme=GetterSetter(None),
    send_welcome_message=GetterSetter(as_boolean),
    volume=GetterSetter(None),
    web_host=GetterSetter(None),
    welcome_message_uri=GetterSetter(unicode),
    )


VALIDATORS = ATTRIBUTES.copy()
for attribute, gettersetter in VALIDATORS.items():
    if gettersetter.decoder is None:
        del VALIDATORS[attribute]



class ListConfiguration(resource.Resource):
    """A mailing list configuration resource."""

    def __init__(self, mailing_list, attribute):
        self._mlist = mailing_list
        self._attribute = attribute

    @resource.GET()
    def get_configuration(self, request):
        """Get a mailing list configuration."""
        resource = {}
        if self._attribute is None:
            # Return all readable attributes.
            for attribute in ATTRIBUTES:
                value = ATTRIBUTES[attribute].get(self._mlist, attribute)
                resource[attribute] = value
        elif self._attribute not in ATTRIBUTES:
            return http.bad_request(
                [], b'Unknown attribute: {0}'.format(self._attribute))
        else:
            attribute = self._attribute
            value = ATTRIBUTES[attribute].get(self._mlist, attribute)
            resource[attribute] = value
        return http.ok([], etag(resource))

    # XXX 2010-09-01 barry: Refactor {put,patch}_configuration() for common
    # code paths.

    def _set_writable_attributes(self, validator, request):
        """Common code for setting all attributes given in the request.

        Returns an HTTP 400 when a request tries to write to a read-only
        attribute.
        """
        converted = validator(request)
        for key, value in converted.items():
            ATTRIBUTES[key].put(self._mlist, key, value)

    @resource.PUT()
    def put_configuration(self, request):
        """Set a mailing list configuration."""
        attribute = self._attribute
        if attribute is None:
            validator = Validator(**VALIDATORS)
            try:
                self._set_writable_attributes(validator, request)
            except ValueError as error:
                return http.bad_request([], str(error))
        elif attribute not in ATTRIBUTES:
            return http.bad_request(
                [], b'Unknown attribute: {0}'.format(attribute))
        elif ATTRIBUTES[attribute].decoder is None:
            return http.bad_request(
                [], b'Read-only attribute: {0}'.format(attribute))
        else:
            validator = Validator(**{attribute: VALIDATORS[attribute]})
            try:
                self._set_writable_attributes(validator, request)
            except ValueError as error:
                return http.bad_request([], str(error))
        return no_content()

    @PATCH()
    def patch_configuration(self, request):
        """Patch the configuration (i.e. partial update)."""
        # Validate only the partial subset of attributes given in the request.
        validationators = {}
        for attribute in request.PATCH:
            if attribute not in ATTRIBUTES:
                return http.bad_request(
                    [], b'Unknown attribute: {0}'.format(attribute))
            elif ATTRIBUTES[attribute].decoder is None:
                return http.bad_request(
                    [], b'Read-only attribute: {0}'.format(attribute))
            else:
                validationators[attribute] = VALIDATORS[attribute]
        validator = Validator(**validationators)
        try:
            self._set_writable_attributes(validator, request)
        except ValueError as error:
            return http.bad_request([], str(error))
        return no_content()
