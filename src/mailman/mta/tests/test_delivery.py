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

"""Test various aspects of email delivery."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestIndividualDelivery',
    ]


import os
import shutil
import tempfile
import unittest

from mailman.app.lifecycle import create_list
from mailman.app.membership import add_member
from mailman.config import config
from mailman.interfaces.mailinglist import Personalization
from mailman.interfaces.member import DeliveryMode
from mailman.mta.deliver import Deliver
from mailman.testing.helpers import (
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



# Global test capture.
_deliveries = []

# Derive this from the default individual delivery class.  The point being
# that we don't want to *actually* attempt delivery of the message to the MTA,
# we just want to capture the messages and metadata dictionaries for
# inspection.
class DeliverTester(Deliver):
    def _deliver_to_recipients(self, mlist, msg, msgdata, recipients):
        _deliveries.append((mlist, msg, msgdata, recipients))
        # Nothing gets refused.
        return []



class TestIndividualDelivery(unittest.TestCase):
    """Test personalized delivery details."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.personalize = Personalization.individual
        # Make Anne a member of this mailing list.
        self._anne = add_member(self._mlist,
                                'anne@example.org', 'Anne Person',
                                'xyz', DeliveryMode.regular, 'en')
        # Clear out any results from the previous test.
        del _deliveries[:]
        self._msg = mfs("""\
From: anne@example.org
To: test@example.com
Subject: test

""")
        # Set up a personalized footer for decoration.
        self._template_dir = tempfile.mkdtemp()
        path = os.path.join(self._template_dir,
                            'site', 'en', 'member-footer.txt')
        os.makedirs(os.path.dirname(path))
        with open(path, 'w') as fp:
            print("""\
address  : $user_address
delivered: $user_delivered_to
language : $user_language
name     : $user_name
options  : $user_optionsurl
""", file=fp)
        config.push('templates', """
        [paths.testing]
        template_dir: {0}
        """.format(self._template_dir))
        self._mlist.footer_uri = 'mailman:///member-footer.txt'
        # Python 2.7 has assertMultiLineEqual.  Let this work without bounds.
        self.maxDiff = None
        self.eq = getattr(self, 'assertMultiLineEqual', self.assertEqual)

    def tearDown(self):
        # Free references.
        del _deliveries[:]
        shutil.rmtree(self._template_dir)
        config.pop('templates')

    def test_member_key(self):
        # 'personalize' should end up in the metadata dictionary so that
        # $user_* keys in headers and footers get filled in correctly.
        msgdata = dict(recipients=['anne@example.org'])
        agent = DeliverTester()
        refused = agent.deliver(self._mlist, self._msg, msgdata)
        self.assertEqual(len(refused), 0)
        self.assertEqual(len(_deliveries), 1)
        _mlist, _msg, _msgdata, _recipients = _deliveries[0]
        member = _msgdata.get('member')
        self.assertEqual(member, self._anne)

    def test_decoration(self):
        msgdata = dict(recipients=['anne@example.org'])
        agent = DeliverTester()
        refused = agent.deliver(self._mlist, self._msg, msgdata)
        self.assertEqual(len(refused), 0)
        self.assertEqual(len(_deliveries), 1)
        _mlist, _msg, _msgdata, _recipients = _deliveries[0]
        self.eq(_msg.as_string(), """\
From: anne@example.org
To: test@example.com
Subject: test
MIME-Version: 1.0
Content-Type: text/plain; charset="us-ascii"
Content-Transfer-Encoding: 7bit


address  : anne@example.org
delivered: anne@example.org
language : English (USA)
name     : Anne Person
options  : http://example.com/anne@example.org

""")
