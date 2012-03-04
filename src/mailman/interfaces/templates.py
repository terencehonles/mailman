# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""Template downloader with cache."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ITemplateLoader',
    ]


from zope.interface import Interface



class ITemplateLoader(Interface):
    """The template downloader utility."""

    def get(uri):
        """Download the named URI, and return the response and content.

        This API uses `urllib2`_ so consult its documentation for details.

        .. _`urllib2`: http://docs.python.org/library/urllib2.html

        :param uri: The URI of the resource.  These may be any URI supported
            by `urllib2` and also `mailman:` URIs for internal resources.
        :type uri: string
        :return: An open file object as defined by urllib2.
        """
