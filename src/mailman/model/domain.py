# Copyright (C) 2008-2009 by the Free Software Foundation, Inc.
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

"""Domains."""

from __future__ import unicode_literals

__metaclass__ = type
__all__ = [
    'Domain',
    'DomainManager',
    ]

from urlparse import urljoin, urlparse
from storm.locals import Int, Unicode
from zope.interface import implements

from mailman.database.model import Model
from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomain, IDomainManager)



class Domain(Model):
    """Domains."""

    implements(IDomain)

    id = Int(primary=True)

    email_host = Unicode()
    base_url = Unicode()
    description = Unicode()
    contact_address = Unicode()

    def __init__(self, email_host,
                 description=None,
                 base_url=None,
                 contact_address=None):
        """Create and register a domain.

        :param email_host: The host name for the email interface.
        :type email_host: string
        :param description: An optional description of the domain.
        :type description: string
        :param base_url: The optional base url for the domain, including
            scheme.  If not given, it will be constructed from the
            `email_host` using the http protocol.
        :type base_url: string
        :param contact_address: The email address to contact a human for this
            domain.  If not given, postmaster@`email_host` will be used.
        :type contact_address: string
        """
        self.email_host = email_host
        self.base_url = (base_url
                         if base_url is not None
                         else 'http://' + email_host)
        self.description = description
        self.contact_address = (contact_address
                                if contact_address is not None
                                else 'postmaster@' + email_host)

    @property
    def url_host(self):
        # pylint: disable-msg=E1101
        # no netloc member; yes it does
        return urlparse(self.base_url).netloc

    def confirm_address(self, token=''):
        """See `IDomain`."""
        return 'confirm-{0}@{1}'.format(token, self.email_host)

    def confirm_url(self, token=''):
        """See `IDomain`."""
        return urljoin(self.base_url, 'confirm/' + token)

    def __repr__(self):
        """repr(a_domain)"""
        if self.description is None:
            return ('<Domain {0.email_host}, base_url: {0.base_url}, '
                    'contact_address: {0.contact_address}>').format(self)
        else:
            return ('<Domain {0.email_host}, {0.description}, '
                    'base_url: {0.base_url}, '
                    'contact_address: {0.contact_address}>').format(self)



class DomainManager:
    """Domain manager."""

    implements(IDomainManager)

    def __init__(self, config):
        """Create a domain manager.

        :param config: The configuration object.
        :type config: `IConfiguration`
        """
        self.config = config
        self.store = config.db.store

    def add(self, email_host,
            description=None,
            base_url=None,
            contact_address=None):
        """See `IDomainManager`."""
        # Be sure the email_host is not already registered.  This is probably
        # a constraint that should (also) be maintained in the database.
        if self.get(email_host) is not None:
            raise BadDomainSpecificationError(
                'Duplicate email host: %s' % email_host)
        domain = Domain(email_host, description, base_url, contact_address)
        self.store.add(domain)
        return domain

    def remove(self, email_host):
        domain = self[email_host]
        self.store.remove(domain)
        return domain

    def get(self, email_host, default=None):
        """See `IDomainManager`."""
        domains = self.store.find(Domain, email_host=email_host)
        if domains.count() < 1:
            return default
        assert domains.count() == 1, (
            'Too many matching domains: %s' % email_host)
        return domains.one()

    def __getitem__(self, email_host):
        """See `IDomainManager`."""
        missing = object()
        domain = self.get(email_host, missing)
        if domain is missing:
            raise KeyError(email_host)
        return domain

    def __len__(self):
        return self.store.find(Domain).count()

    def __iter__(self):
        """See `IDomainManager`."""
        for domain in self.store.find(Domain):
            yield domain

    def __contains__(self, email_host):
        """See `IDomainManager`."""
        return self.store.find(Domain, email_host=email_host).count() > 0
