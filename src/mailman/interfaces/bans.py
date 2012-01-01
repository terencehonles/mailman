# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Manager of email address bans."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IBan',
    'IBanManager',
    ]


from zope.interface import Attribute, Interface



class IBan(Interface):
    """A specific ban.

    In general, this interface isn't publicly useful.
    """

    email = Attribute('The banned email address, or pattern.')

    mailing_list = Attribute(
        """The fqdn name of the mailing list the ban applies to.

        Use None if this is a global ban.
        """)



class IBanManager(Interface):
    """The global manager of email address bans."""

    def ban(email, mailing_list=None):
        """Ban an email address from subscribing to a mailing list.

        When an email address is banned, it will not be allowed to subscribe
        to a the named mailing list.  This does not affect any email address
        already subscribed to the mailing list.  With the default arguments,
        an email address can be banned globally from subscribing to any
        mailing list on the system.

        It is also possible to add a 'ban pattern' whereby all email addresses
        matching a Python regular expression can be banned.  This is
        accomplished by using a `^` as the first character in `email`.

        When an email address is already banned for the given mailing list (or
        globally), then this method does nothing.  However, it is possible to
        extend a ban for a specific mailing list into a global ban; both bans
        would be in place and they can be removed individually.

        :param email: The text email address being banned or, if the string
            starts with a caret (^), the email address pattern to ban.
        :type email: str
        :param mailing_list: The fqdn name of the mailing list to which the
            ban applies.  If None, then the ban is global.
        :type mailing_list: string
        """

    def unban(email, mailing_list=None):
        """Remove an email address ban.

        This removes a specific or global email address ban, which would have
        been added with the `ban()` method.  If a ban is lifted which did not
        exist, this method does nothing.

        :param email: The text email address being unbanned or, if the string
            starts with a caret (^), the email address pattern to unban.
        :type email: str
        :param mailing_list: The fqdn name of the mailing list to which the
            unban applies.  If None, then the unban is global.
        :type mailing_list: string
        """

    def is_banned(email, mailing_list=None):
        """Check whether a specific email address is banned.

        `email` must be a text email address; it cannot be a pattern.  The
        given email address is checked against all registered bans, both
        specific and regular expression, both for the named mailing list (if
        given), and globally.

        :param email: The text email address being checked.
        :type email: str
        :param mailing_list: The fqdn name of the mailing list being checked.
            Note that if not None, both specific and global bans will be
            checked.  If None, then only global bans will be checked.
        :type mailing_list: string
        :return: A flag indicating whether the given email address is banned
            or not.
        :rtype: bool
        """
