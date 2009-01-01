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

from zope.interface import Interface, Attribute



class IDomain(Interface):
    """Interface representing domains."""

    email_host = Attribute(
        """The host name for email for this domain.

        :type: string
        """)

    url_host = Attribute(
        """The host name for the web interface for this domain.

        :type: string
        """)

    base_url = Attribute(
        """The base url for the Mailman server at this domain.

        The base url includes the scheme and host name.

        :type: string
        """)

    description = Attribute(
        """The human readable description of the domain name.

        :type: string
        """)

    contact_address = Attribute(
        """The contact address for the human at this domain.

        E.g. postmaster@python.org.

        :type: string
        """)

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
