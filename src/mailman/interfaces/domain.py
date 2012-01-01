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

"""Interface representing domains."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BadDomainSpecificationError',
    'DomainCreatedEvent',
    'DomainCreatingEvent',
    'DomainDeletedEvent',
    'DomainDeletingEvent',
    'IDomain',
    'IDomainManager',
    ]


from zope.interface import Interface, Attribute

from mailman.core.errors import MailmanError



class BadDomainSpecificationError(MailmanError):
    """The specification of a virtual domain is invalid or duplicated."""

    def __init__(self, domain):
        super(BadDomainSpecificationError, self).__init__(domain)
        self.domain = domain


class DomainCreatingEvent:
    """A domain is about to be created."""

    def __init__(self, mail_host):
        self.mail_host = mail_host


class DomainCreatedEvent:
    """A domain was created."""

    def __init__(self, domain):
        self.domain = domain


class DomainDeletingEvent:
    """A domain is about to be deleted."""

    def __init__(self, domain):
        self.domain = domain


class DomainDeletedEvent:
    """A domain was deleted."""

    def __init__(self, mail_host):
        self.mail_host = mail_host



class IDomain(Interface):
    """Interface representing domains."""

    mail_host = Attribute('The host name for email for this domain.')

    url_host = Attribute(
        'The host name for the web interface for this domain.')

    base_url = Attribute("""\
    The base url for the Mailman server at this domain, which includes the
    scheme and host name.""")

    scheme = Attribute(
        """The protocol scheme used to contact this list's server.""")

    description = Attribute(
        'The human readable description of the domain name.')

    contact_address = Attribute("""\
    The contact address for the human at this domain.
    E.g. postmaster@example.com""")

    mailing_lists = Attribute(
        'All mailing lists for this domain.')

    def confirm_url(token=''):
        """The url used for various forms of confirmation.

        :param token: The confirmation token to use in the url.
        :type token: string
        :return: The confirmation url.
        :rtype: string
        """



class IDomainManager(Interface):
    """The manager of domains."""

    def add(mail_host, description=None, base_url=None, contact_address=None):
        """Add a new domain.

        :param mail_host: The email host name for the domain.
        :type mail_host: string
        :param description: The description of the domain.
        :type description: string
        :param base_url: The base url, including the scheme for the web
            interface of the domain.  If not given, it defaults to
            http://`mail_host`/
        :type base_url: string
        :param contact_address: The email contact address for the human
            managing the domain.  If not given, defaults to
            postmaster@`mail_host`
        :type contact_address: string
        :return: The new domain object
        :rtype: `IDomain`
        :raises `BadDomainSpecificationError`: when the `mail_host` is
            already registered.
        """

    def remove(mail_host):
        """Remove the domain.

        :param mail_host: The email host name of the domain to remove.
        :type mail_host: string
        :raises KeyError: if the named domain does not exist.
        """

    def __getitem__(mail_host):
        """Return the named domain.

        :param mail_host: The email host name of the domain to remove.
        :type mail_host: string
        :return: The domain object.
        :rtype: `IDomain`
        :raises KeyError: if the named domain does not exist.
        """

    def get(mail_host, default=None):
        """Return the named domain.

        :param mail_host: The email host name of the domain to remove.
        :type mail_host: string
        :param default: What to return if the named domain does not exist.
        :type default: object
        :return: The domain object or None if the named domain does not exist.
        :rtype: `IDomain`
        """

    def __iter__():
        """An iterator over all the domains.

        :return: iterator over `IDomain`.
        """

    def __contains__(mail_host):
        """Is this a known domain?

        :param mail_host: An email host name.
        :type mail_host: string
        :return: True if this domain is known.
        :rtype: bool
        """
