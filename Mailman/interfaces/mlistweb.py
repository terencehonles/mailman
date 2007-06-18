# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

"""Interface for the web addresses associated with a mailing list."""

from zope.interface import Interface, Attribute



class IMailingListWeb(Interface):
    """The web addresses associated with a mailing list."""

    protocol = Attribute(
        """The protocol scheme used to contact this list's server.

        The web server on thi protocol provides the web interface for this
        mailing list.  The protocol scheme should be 'http' or 'https'.""")

    web_host = Attribute(
        """This list's web server's domain.

        The read-only domain name of the host to contact for interacting with
        the web interface of the mailing list.""")

    def script_url(target, context=None):
        """Return the url to the given script target.

        If 'context' is not given, or is None, then an absolute url is
        returned.  If context is given, it must be an IMailingListRequest
        object, and the returned url will be relative to that object's
        'location' attribute.
        """
