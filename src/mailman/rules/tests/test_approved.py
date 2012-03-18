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

"""Test the mime_delete handler."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestApproved',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.core import errors
from mailman.interfaces.action import FilterAction
from mailman.interfaces.member import MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.rules import approved
from mailman.testing.helpers import (
    LogFileMark,
    get_queue_messages,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestApproved(unittest.TestCase):
    """Test the approved handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._rule = approved.Approved()
        self._msg = mfs("""\
From: anne@example.com
To: test@example.com
Subject: A Message with non-ascii body
Message-ID: <ant>
MIME-Version: 1.0
Content-Type: text/plain; charset="iso-8859-1"
Content-Transfer-Encoding: quoted-printable

This is a message body with a non-ascii character =E4

""")

    def test_approved_nonascii(self):
        result = True
        try:
            result = self._rule.check(self._mlist, self._msg, {})
        except (UnicodeError, UnicodeWarning):
            raise AssertionError('Non-ascii message raised UnicodeError')
        self.assertEqual(result, False)
