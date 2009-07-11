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
    'IDomain',
    'IDomainSet',
    ]


from lazr.restful.declarations import (
    collection_default_content, export_as_webservice_collection,
    export_as_webservice_entry, exported)
from zope.interface import Interface, Attribute
from zope.schema import TextLine

from mailman.i18n import _



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



class IDomainSet(Interface):
    """The set of all known domains."""

    export_as_webservice_collection(IDomain)

    @collection_default_content()
    def get_domains():
        """The list of all domains.

        :return: The list of all known domains.
        :rtype: list of `IDomain`
        """
