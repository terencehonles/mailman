# Copyright (C) 2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Domains."""

__metaclass__ = type
__all__ = [
    'Domain',
    ]

from urlparse import urljoin, urlparse
from zope.interface import implements

from mailman.interfaces.domain import IDomain



class Domain:
    """Domains."""

    implements(IDomain)

    def __init__(self, email_host, base_url=None, description=None,
                 contact_address=None):
        """Create and register a domain.

        :param email_host: The host name for the email interface.
        :type email_host: string
        :param base_url: The optional base url for the domain, including
            scheme.  If not given, it will be constructed from the
            `email_host` using the http protocol.
        :type base_url: string
        :param description: An optional description of the domain.
        :type description: string
        :type contact_address: The email address to contact a human for this
            domain.  If not given, postmaster@`email_host` will be used.
        """
        self.email_host = email_host
        self.base_url = (base_url if base_url is not None else
                         'http://' + email_host)
        self.description = description
        self.contact_address = (contact_address
                                if contact_address is not None
                                else 'postmaster@' + email_host)
        self.url_host = urlparse(self.base_url).netloc

    def confirm_address(self, token=''):
        """See `IDomain`."""
        return 'confirm-%s@%s' % (token, self.email_host)

    def confirm_url(self, token=''):
        """See `IDomain`."""
        return urljoin(self.base_url, 'confirm/' + token)
