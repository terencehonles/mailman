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

"""Interface representing domains."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BadDomainSpecificationError',
    'IDomain',
    'IDomainCollection',
    'IDomainManager',
    ]


from lazr.restful.declarations import (
    collection_default_content, error_status, export_as_webservice_collection,
    export_as_webservice_entry, export_factory_operation, exported)
from zope.interface import Interface, Attribute
from zope.schema import TextLine

from mailman.core.errors import MailmanError
from mailman.core.i18n import _



@error_status(400)
class BadDomainSpecificationError(MailmanError):
    """The specification of a virtual domain is invalid or duplicated."""



class IDomain(Interface):
    """Interface representing domains."""

    export_as_webservice_entry()

    email_host = exported(TextLine(
        title=_('Email host name'),
        description=_('The host name for email for this domain.'),
        ))

    url_host = exported(TextLine(
        title=_('Web host name'),
        description=_('The host name for the web interface for this domain.')
        ))

    base_url = exported(TextLine(
        title=_('Base URL'),
        description=_("""\
        The base url for the Mailman server at this domain, which includes the
        scheme and host name."""),
        ))

    description = exported(TextLine(
        title=_('Description'),
        description=_('The human readable description of the domain name.'),
        ))

    contact_address = exported(TextLine(
        title=_('Contact address'),
        description=_("""\
        The contact address for the human at this domain.

        E.g. postmaster@example.com"""),
        ))

    def confirm_address(token=''):
        """The address used for various forms of email confirmation.

        :param token: The confirmation token to use in the email address.
        :type token: string
        :return: The email confirmation address.
        :rtype: string
        """

    def confirm_url(token=''):
        """The url used for various forms of confirmation.

        :param token: The confirmation token to use in the url.
        :type token: string
        :return: The confirmation url.
        :rtype: string
        """



class IDomainManager(Interface):
    """The manager of domains."""

    def add(email_host, description=None, base_url=None, contact_address=None):
        """Add a new domain.

        :param email_host: The email host name for the domain.
        :type email_host: string
        :param description: The description of the domain.
        :type description: string
        :param base_url: The base url, including the scheme for the web
            interface of the domain.  If not given, it defaults to
            http://`email_host`/
        :type base_url: string
        :param contact_address: The email contact address for the human
            managing the domain.  If not given, defaults to
            postmaster@`email_host`
        :type contact_address: string
        :return: The new domain object
        :rtype: `IDomain`
        :raises `BadDomainSpecificationError`: when the `email_host` is
            already registered.
        """

    def remove(email_host):
        """Remove the domain.

        :param email_host: The email host name of the domain to remove.
        :type email_host: string
        :raises KeyError: if the named domain does not exist.
        """

    def __getitem__(email_host):
        """Return the named domain.

        :param email_host: The email host name of the domain to remove.
        :type email_host: string
        :return: The domain object.
        :rtype: `IDomain`
        :raises KeyError: if the named domain does not exist.
        """

    def get(email_host, default=None):
        """Return the named domain.

        :param email_host: The email host name of the domain to remove.
        :type email_host: string
        :param default: What to return if the named domain does not exist.
        :type default: object
        :return: The domain object or None if the named domain does not exist.
        :rtype: `IDomain`
        """

    def __iter__():
        """An iterator over all the domains.

        :return: iterator over `IDomain`.
        """

    def __contains__(email_host):
        """Is this a known domain?

        :param email_host: An email host name.
        :type email_host: string
        :return: True if this domain is known.
        :rtype: bool
        """



class IDomainCollection(Interface):
    """The set of domains available via the REST API."""

    export_as_webservice_collection(IDomain)

    @collection_default_content()
    def get_domains():
        """The list of all domains.

        :return: The list of all known domains.
        :rtype: list of `IDomain`
        """

    @export_factory_operation(
        IDomain,
        ('email_host', 'description', 'base_url', 'contact_address'))
    def new(email_host, description=None, base_url=None, contact_address=None):
        """Add a new domain.

        :param email_host: The email host name for the domain.
        :type email_host: string
        :param description: The description of the domain.
        :type description: string
        :param base_url: The base url, including the scheme for the web
            interface of the domain.  If not given, it defaults to
            http://`email_host`/
        :type base_url: string
        :param contact_address: The email contact address for the human
            managing the domain.  If not given, defaults to
            postmaster@`email_host`
        :type contact_address: string
        :return: The new domain object
        :rtype: `IDomain`
        :raises `BadDomainSpecificationError`: when the `email_host` is
            already registered.
        """
