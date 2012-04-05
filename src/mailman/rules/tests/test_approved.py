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

"""Test the `approved` handler."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestApproved',
    'TestApprovedNonASCII',
    'TestApprovedPseudoHeader',
    'TestApprovedPseudoHeaderMIME',
    ]


import unittest

from flufl.password import lookup, make_secret

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.rules import approved
from mailman.testing.helpers import (
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestApproved(unittest.TestCase):
    """Test the approved handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        scheme = lookup(config.passwords.password_scheme.upper())
        self._mlist.moderator_password = make_secret('super secret', scheme)
        self._rule = approved.Approved()
        self._msg = mfs("""\
From: anne@example.com
To: test@example.com
Subject: A Message with non-ascii body
Message-ID: <ant>
MIME-Version: 1.0

A message body.
""")

    def test_approved_header(self):
        self._msg['Approved'] = 'super secret'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_approve_header(self):
        self._msg['Approve'] = 'super secret'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_x_approved_header(self):
        self._msg['X-Approved'] = 'super secret'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_x_approve_header(self):
        self._msg['X-Approve'] = 'super secret'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_approved_header_wrong_password(self):
        self._msg['Approved'] = 'not the password'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_approve_header_wrong_password(self):
        self._msg['Approve'] = 'not the password'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_x_approved_header_wrong_password(self):
        self._msg['X-Approved'] = 'not the password'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_x_approve_header_wrong_password(self):
        self._msg['X-Approve'] = 'not the password'
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_removes_approved_header(self):
        self._msg['Approved'] = 'super secret'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['approved'], None)

    def test_removes_approve_header(self):
        self._msg['Approve'] = 'super secret'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['approve'], None)

    def test_removes_x_approved_header(self):
        self._msg['X-Approved'] = 'super secret'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['x-approved'], None)

    def test_removes_x_approve_header(self):
        self._msg['X-Approve'] = 'super secret'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['x-approve'], None)

    def test_removes_approved_header_wrong_password(self):
        self._msg['Approved'] = 'not the password'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['approved'], None)

    def test_removes_approve_header_wrong_password(self):
        self._msg['Approve'] = 'not the password'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['approve'], None)

    def test_removes_x_approved_header_wrong_password(self):
        self._msg['X-Approved'] = 'not the password'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['x-approved'], None)

    def test_removes_x_approve_header_wrong_password(self):
        self._msg['X-Approve'] = 'not the password'
        self._rule.check(self._mlist, self._msg, {})
        self.assertEqual(self._msg['x-approve'], None)



class TestApprovedPseudoHeader(unittest.TestCase):
    """Test the approved handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        scheme = lookup(config.passwords.password_scheme.upper())
        self._mlist.moderator_password = make_secret('super secret', scheme)
        self._rule = approved.Approved()
        self._msg = mfs("""\
From: anne@example.com
To: test@example.com
Subject: A Message with non-ascii body
Message-ID: <ant>
MIME-Version: 1.0

""")

    def test_approved_pseudo_header(self):
        self._msg.set_payload("""\
Approved: super secret
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_approve_pseudo_header(self):
        self._msg.set_payload("""\
Approve: super secret
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_x_approved_pseudo_header(self):
        self._msg.set_payload("""\
X-Approved: super secret
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_x_approve_pseudo_header(self):
        self._msg.set_payload("""\
X-Approve: super secret
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertTrue(result)

    def test_approved_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
Approved: not the password
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_approve_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
Approve: not the password
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_x_approved_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
X-Approved: not the password
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_x_approve_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
X-Approve: not the password
        """)
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)

    def test_removes_approved_pseudo_header(self):
        self._msg.set_payload("""\
Approved: super secret
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('Approved' in self._msg.get_payload())

    def test_removes_approve_pseudo_header(self):
        self._msg.set_payload("""\
Approve: super secret
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('Approve' in self._msg.get_payload())

    def test_removes_x_approved_pseudo_header(self):
        self._msg.set_payload("""\
X-Approved: super secret
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('X-Approved' in self._msg.get_payload())

    def test_removes_x_approve_pseudo_header(self):
        self._msg.set_payload("""\
X-Approve: super secret
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('X-Approve' in self._msg.get_payload())

    def test_removes_approved_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
Approved: not the password
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('Approved' in self._msg.get_payload())

    def test_removes_approve_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
Approve: not the password
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('Approve' in self._msg.get_payload())

    def test_removes_x_approved_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
X-Approved: not the password
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('X-Approved' in self._msg.get_payload())

    def test_removes_x_approve_pseudo_header_wrong_password(self):
        self._msg.set_payload("""\
X-Approve: not the password
        """)
        self._rule.check(self._mlist, self._msg, {})
        self.assertFalse('X-Approve' in self._msg.get_payload())



class TestApprovedPseudoHeaderMIME(unittest.TestCase):
    """Test the approved handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        scheme = lookup(config.passwords.password_scheme.upper())
        self._mlist.moderator_password = make_secret('super secret', scheme)
        self._rule = approved.Approved()
        self._msg_text_template = """\
From: anne@example.com
To: test@example.com
Subject: A Message with non-ascii body
Message-ID: <ant>
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="AAA"

--AAA
Content-Type: application/x-ignore

{0}: not the password
The above line will be ignored.

--AAA
Content-Type: text/plain

{0}: {1}
An important message.

"""

    def test_approved_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('Approved', 'super secret'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertTrue(result)

    def test_approve_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('Approve', 'super secret'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertTrue(result)

    def test_x_approved_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approved', 'super secret'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertTrue(result)

    def test_x_approve_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approve', 'super secret'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertTrue(result)

    def test_approved_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('Approved', 'not password'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertFalse(result)

    def test_approve_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('Approve', 'not password'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertFalse(result)

    def test_x_approved_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approved', 'not password'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertFalse(result)

    def test_x_approve_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approve', 'not password'))
        result = self._rule.check(self._mlist, msg, {})
        self.assertFalse(result)

    def test_removes_approved_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('Approved', 'super secret'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('Approved' in msg.get_payload(1).get_payload())

    def test_removes_approve_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('Approve', 'super secret'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('Approve' in msg.get_payload(1).get_payload())

    def test_removes_x_approved_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approved', 'super secret'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('X-Approved' in msg.get_payload(1).get_payload())

    def test_removes_x_approve_pseudo_header_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approve', 'super secret'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('X-Approve' in msg.get_payload(1).get_payload())

    def test_removes_approved_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('Approved', 'not password'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('Approved' in msg.get_payload(1).get_payload())

    def test_removes_approve_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('Approve', 'not password'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('Approve' in msg.get_payload(1).get_payload())

    def test_removes_x_approved_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approved', 'not password'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('X-Approved' in msg.get_payload(1).get_payload())

    def test_removes_x_approve_pseudo_header_wrong_password_mime(self):
        msg = mfs(self._msg_text_template.format('X-Approve', 'not password'))
        self._rule.check(self._mlist, msg, {})
        self.assertFalse('X-Approve' in msg.get_payload(1).get_payload())



class TestApprovedNonASCII(unittest.TestCase):
    """Test the approved handler with non-ascii messages."""

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

    def test_nonascii_body_missing_header(self):
        # When the message body contains non-ascii, the rule should not throw
        # unicode errors.  LP: #949924.
        result = self._rule.check(self._mlist, self._msg, {})
        self.assertFalse(result)
