# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""Testing app.bounces functions."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import os
import shutil
import tempfile
import unittest

from zope.component import getUtility

from mailman.app.bounces import StandardVERP, send_probe
from mailman.app.lifecycle import create_list
from mailman.app.membership import add_member
from mailman.config import config
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.member import DeliveryMode
from mailman.interfaces.pending import IPendings
from mailman.testing.helpers import (
    get_queue_messages,
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import ConfigLayer



class TestVERP(unittest.TestCase):
    """Test header VERP detection."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._verper = StandardVERP()

    def test_no_verp(self):
        # The empty set is returned when there is no VERP headers.
        msg = message_from_string("""\
From: postmaster@example.com
To: mailman-bounces@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg), set())

    def test_verp_in_to(self):
        # A VERP address is found in the To header.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org']))

    def test_verp_in_delivered_to(self):
        # A VERP address is found in the Delivered-To header.
        msg = message_from_string("""\
From: postmaster@example.com
Delivered-To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org']))

    def test_verp_in_envelope_to(self):
        # A VERP address is found in the Envelope-To header.
        msg = message_from_string("""\
From: postmaster@example.com
Envelope-To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org']))

    def test_verp_in_apparently_to(self):
        # A VERP address is found in the Apparently-To header.
        msg = message_from_string("""\
From: postmaster@example.com
Apparently-To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org']))

    def test_verp_with_empty_header(self):
        # A VERP address is found, but there's an empty header.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To:

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org']))

    def test_no_verp_with_empty_header(self):
        # There's an empty header, and no VERP address is found.
        msg = message_from_string("""\
From: postmaster@example.com
To:

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg), set())

    def test_verp_with_non_match(self):
        # A VERP address is found, but a header had a non-matching pattern.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To: test-bounces@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org']))

    def test_no_verp_with_non_match(self):
        # No VERP address is found, and a header had a non-matching pattern.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg), set())

    def test_multiple_verps(self):
        # More than one VERP address was found in the same header.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org']))

    def test_multiple_verps_different_values(self):
        # More than one VERP address was found in the same header with
        # different values.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To: test-bounces+bart=example.org@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org', 'bart@example.org']))

    def test_multiple_verps_different_values_different_headers(self):
        # More than one VERP address was found in different headers with
        # different values.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
Apparently-To: test-bounces+bart=example.org@example.com

""")
        self.assertEqual(self._verper.get_verp(self._mlist, msg),
                         set(['anne@example.org', 'bart@example.org']))



class TestSendProbe(unittest.TestCase):
    """Test sending of the probe message."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._member = add_member(self._mlist, 'anne@example.com',
                                  'Anne Person', 'xxx',
                                  DeliveryMode.regular, 'en')
        self._msg = message_from_string("""\
From: bouncer@example.com
To: anne@example.com
Subject: You bounced
Message-ID: <first>

""")

    def test_token(self):
        # Show that send_probe() returns a proper token, and that the token
        # corresponds to a record in the pending database.
        token = send_probe(self._member, self._msg)
        pendable = getUtility(IPendings).confirm(token)
        self.assertEqual(len(pendable.items()), 2)
        self.assertEqual(set(pendable.keys()),
                         set(['member_id', 'message_id']))
        self.assertEqual(pendable['member_id'], self._member.member_id)
        self.assertEqual(pendable['message_id'], '<first>')

    def test_probe_is_multipart(self):
        # The probe is a multipart/mixed with two subparts.
        send_probe(self._member, self._msg)
        message = get_queue_messages('virgin')[0].msg
        self.assertEqual(message.get_content_type(), 'multipart/mixed')
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)

    def test_probe_sends_one_message(self):
        # send_probe() places one message in the virgin queue.
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 0)
        send_probe(self._member, self._msg)
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 1)

    def test_probe_contains_original(self):
        # Show that send_probe() places a properly formatted message in the
        # virgin queue.
        send_probe(self._member, self._msg)
        message = get_queue_messages('virgin')[0].msg
        rfc822 = message.get_payload(1)
        self.assertEqual(rfc822.get_content_type(), 'message/rfc822')
        self.assertTrue(rfc822.is_multipart())
        self.assertEqual(len(rfc822.get_payload()), 1)
        self.assertEqual(rfc822.get_payload(0).as_string(),
                         self._msg.as_string())

    def test_notice(self):
        # Test that the notice in the first subpart is correct.
        send_probe(self._member, self._msg)
        message = get_queue_messages('virgin')[0].msg
        notice = message.get_payload(0)
        self.assertEqual(notice.get_content_type(), 'text/plain')
        # The interesting bits are the parts that have been interpolated into
        # the message.  For now the best we can do is know that the
        # interpolation values appear in the message.  When Python 2.7 is our
        # minimum requirement, we can use assertRegexpMatches().
        body = notice.get_payload()
        self.assertTrue('test@example.com' in body)
        self.assertTrue('anne@example.com' in body)
        self.assertTrue('http://example.com/anne@example.com' in body)
        self.assertTrue('test-owner@example.com' in body)

    def test_headers(self):
        # Check the headers of the outer message.
        token = send_probe(self._member, self._msg)
        message = get_queue_messages('virgin')[0].msg
        self.assertEqual(message['From'],
                         'test-bounces+{0}@example.com'.format(token))
        self.assertEqual(message['To'], 'anne@example.com')
        self.assertEqual(message['Subject'], 'Test mailing list probe message')



class TestSendProbeNonEnglish(unittest.TestCase):
    """Test sending of the probe message to a non-English speaker."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._member = add_member(self._mlist, 'anne@example.com',
                                  'Anne Person', 'xxx',
                                  DeliveryMode.regular, 'en')
        self._msg = message_from_string("""\
From: bouncer@example.com
To: anne@example.com
Subject: You bounced
Message-ID: <first>

""")
        # Set up the translation context.
        self._template_dir = tempfile.mkdtemp()
        xx_template_path = os.path.join(
            self._template_dir, 't', 'xx', 'probe.txt')
        os.makedirs(os.path.dirname(xx_template_path))
        config.push('xx template dir', """\
        [paths.testing]
        template_dir: {0}/t
        var_dir: {0}/v
        """.format(self._template_dir))
        language_manager = getUtility(ILanguageManager)
        language_manager.add('xx', 'utf-8', 'Freedonia')
        self._member.preferences.preferred_language = 'xx'
        with open(xx_template_path, 'w') as fp:
            print >> fp, """\
blah blah blah
$listname
$address
$optionsurl
$owneraddr
"""

    def tearDown(self):
        config.pop('xx template dir')
        shutil.rmtree(self._template_dir)

    def test_subject_with_member_nonenglish(self):
        # Test that members with non-English preferred language get a Subject
        # header in the expected language.
        send_probe(self._member, self._msg)
        message = get_queue_messages('virgin')[0].msg
        self.assertEqual(
            message['Subject'],
            '=?utf-8?q?ailing-may_ist-lay_Test_obe-pray_essage-may?=')

    def test_probe_notice_with_member_nonenglish(self):
        # Test that a member with non-English preferred language gets the
        # probe message in their language.
        send_probe(self._member, self._msg)
        message = get_queue_messages('virgin')[0].msg
        notice = message.get_payload(0).get_payload()
        self.assertEqual(notice, """\
blah blah blah test@example.com anne@example.com
http://example.com/anne@example.com test-owner@example.com""")



class TestProbe(unittest.TestCase):
    """Test VERP probing."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')





def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestProbe))
    suite.addTest(unittest.makeSuite(TestSendProbe))
    suite.addTest(unittest.makeSuite(TestSendProbeNonEnglish))
    suite.addTest(unittest.makeSuite(TestVERP))
    return suite
