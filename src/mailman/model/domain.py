# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Domain',
    'DomainManager',
    ]


from urlparse import urljoin, urlparse
from storm.locals import Int, Unicode
from zope.event import notify
from zope.interface import implementer

from mailman.database.model import Model
from mailman.database.transaction import dbconnection
from mailman.interfaces.domain import (
    BadDomainSpecificationError, DomainCreatedEvent, DomainCreatingEvent,
    DomainDeletedEvent, DomainDeletingEvent, IDomain, IDomainManager)
from mailman.model.mailinglist import MailingList



@implementer(IDomain)
class Domain(Model):
    """Domains."""

    id = Int(primary=True)

    mail_host = Unicode()
    base_url = Unicode()
    description = Unicode()
    contact_address = Unicode()

    def __init__(self, mail_host,
                 description=None,
                 base_url=None,
                 contact_address=None):
        """Create and register a domain.

        :param mail_host: The host name for the email interface.
        :type mail_host: string
        :param description: An optional description of the domain.
        :type description: string
        :param base_url: The optional base url for the domain, including
            scheme.  If not given, it will be constructed from the
            `mail_host` using the http protocol.
        :type base_url: string
        :param contact_address: The email address to contact a human for this
            domain.  If not given, postmaster@`mail_host` will be used.
        :type contact_address: string
        """
        self.mail_host = mail_host
        self.base_url = (base_url
                         if base_url is not None
                         else 'http://' + mail_host)
        self.description = description
        self.contact_address = (contact_address
                                if contact_address is not None
                                else 'postmaster@' + mail_host)

    @property
    def url_host(self):
        """See `IDomain`."""
        return urlparse(self.base_url).netloc

    @property
    def scheme(self):
        """See `IDomain`."""
        return urlparse(self.base_url).scheme

    @property
    @dbconnection
    def mailing_lists(self, store):
        """See `IDomain`."""
        mailing_lists = store.find(
            MailingList,
            MailingList.mail_host == self.mail_host)
        for mlist in mailing_lists:
            yield mlist

    def confirm_url(self, token=''):
        """See `IDomain`."""
        return urljoin(self.base_url, 'confirm/' + token)

    def __repr__(self):
        """repr(a_domain)"""
        if self.description is None:
            return ('<Domain {0.mail_host}, base_url: {0.base_url}, '
                    'contact_address: {0.contact_address}>').format(self)
        else:
            return ('<Domain {0.mail_host}, {0.description}, '
                    'base_url: {0.base_url}, '
                    'contact_address: {0.contact_address}>').format(self)



@implementer(IDomainManager)
class DomainManager:
    """Domain manager."""

    @dbconnection
    def add(self, store,
            mail_host,
            description=None,
            base_url=None,
            contact_address=None):
        """See `IDomainManager`."""
        # Be sure the mail_host is not already registered.  This is probably
        # a constraint that should (also) be maintained in the database.
        if self.get(mail_host) is not None:
            raise BadDomainSpecificationError(
                'Duplicate email host: %s' % mail_host)
        notify(DomainCreatingEvent(mail_host))
        domain = Domain(mail_host, description, base_url, contact_address)
        store.add(domain)
        notify(DomainCreatedEvent(domain))
        return domain

    @dbconnection
    def remove(self, store, mail_host):
        domain = self[mail_host]
        notify(DomainDeletingEvent(domain))
        store.remove(domain)
        notify(DomainDeletedEvent(mail_host))
        return domain

    @dbconnection
    def get(self, store, mail_host, default=None):
        """See `IDomainManager`."""
        domains = store.find(Domain, mail_host=mail_host)
        if domains.count() < 1:
            return default
        assert domains.count() == 1, (
            'Too many matching domains: %s' % mail_host)
        return domains.one()

    def __getitem__(self, mail_host):
        """See `IDomainManager`."""
        missing = object()
        domain = self.get(mail_host, missing)
        if domain is missing:
            raise KeyError(mail_host)
        return domain

    @dbconnection
    def __len__(self, store):
        return store.find(Domain).count()

    @dbconnection
    def __iter__(self, store):
        """See `IDomainManager`."""
        for domain in store.find(Domain):
            yield domain

    @dbconnection
    def __contains__(self, store, mail_host):
        """See `IDomainManager`."""
        return store.find(Domain, mail_host=mail_host).count() > 0
