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

"""Testing various recipients stuff."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestMemberRecipients',
    'TestOwnerRecipients',
    ]


import unittest

from zope.component import getUtility
from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.member import DeliveryMode, DeliveryStatus, MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import specialized_message_from_string as mfs
from mailman.testing.layers import ConfigLayer



class TestMemberRecipients(unittest.TestCase):
    """Test regular member recipient calculation."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._manager = getUtility(IUserManager)
        anne = self._manager.create_address('anne@example.com')
        bart = self._manager.create_address('bart@example.com')
        cris = self._manager.create_address('cris@example.com')
        dave = self._manager.create_address('dave@example.com')
        self._anne = self._mlist.subscribe(anne, MemberRole.member)
        self._bart = self._mlist.subscribe(bart, MemberRole.member)
        self._cris = self._mlist.subscribe(cris, MemberRole.member)
        self._dave = self._mlist.subscribe(dave, MemberRole.member)
        self._process = config.handlers['member-recipients'].process
        self._msg = mfs("""\
From: Elle Person <elle@example.com>
To: test@example.com

""")

    def test_shortcircuit(self):
        # When there are already recipients in the message metadata, those are
        # used instead of calculating them from the list membership.
        recipients = set(('zperson@example.com', 'yperson@example.com'))
        msgdata = dict(recipients=recipients)
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], recipients)

    def test_calculate_recipients(self):
        # The normal path just adds the list's regular members.
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('anne@example.com',
                                                     'bart@example.com',
                                                     'cris@example.com',
                                                     'dave@example.com')))

    def test_digest_members_not_included(self):
        # Digest members are not included in the recipients calculated by this
        # handler.
        self._cris.preferences.delivery_mode = DeliveryMode.mime_digests
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('anne@example.com',
                                                     'bart@example.com',
                                                     'dave@example.com')))



class TestOwnerRecipients(unittest.TestCase):
    """Test owner recipient calculation."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._manager = getUtility(IUserManager)
        anne = self._manager.create_address('anne@example.com')
        bart = self._manager.create_address('bart@example.com')
        cris = self._manager.create_address('cris@example.com')
        dave = self._manager.create_address('dave@example.com')
        # Make Cris and Dave owners of the mailing list.
        self._anne = self._mlist.subscribe(anne, MemberRole.member)
        self._bart = self._mlist.subscribe(bart, MemberRole.member)
        self._cris = self._mlist.subscribe(cris, MemberRole.owner)
        self._dave = self._mlist.subscribe(dave, MemberRole.owner)
        self._process = config.handlers['owner-recipients'].process
        self._msg = mfs("""\
From: Elle Person <elle@example.com>
To: test-owner@example.com

""")

    def test_shortcircuit(self):
        # When there are already recipients in the message metadata, those are
        # used instead of calculating them from the owner membership.
        recipients = set(('zperson@example.com', 'yperson@example.com'))
        msgdata = dict(recipients=recipients)
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], recipients)

    def test_calculate_recipients(self):
        # The normal path just adds the list's owners.
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('cris@example.com',
                                                     'dave@example.com')))

    def test_with_moderators(self):
        # Moderators are included in the owner recipient list.
        elle = self._manager.create_address('elle@example.com')
        fred = self._manager.create_address('fred@example.com')
        gwen = self._manager.create_address('gwen@example.com')
        self._mlist.subscribe(elle, MemberRole.moderator)
        self._mlist.subscribe(fred, MemberRole.moderator)
        self._mlist.subscribe(gwen, MemberRole.owner)
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('cris@example.com',
                                                     'dave@example.com',
                                                     'elle@example.com',
                                                     'fred@example.com',
                                                     'gwen@example.com')))

    def test_dont_decorate(self):
        # Messages to the administrators don't get decorated.
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertTrue(msgdata['nodecorate'])

    def test_omit_disabled_owners(self):
        # Owner memberships can be disabled, and these folks will not get the
        # messages.
        self._dave.preferences.delivery_status = DeliveryStatus.by_user
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('cris@example.com',)))

    def test_include_membership_disabled_owner_enabled(self):
        # If an address is subscribed to a mailing list as both an owner and a
        # member, and their membership is disabled but their ownership
        # subscription is not, they still get owner email.
        dave = self._manager.get_address('dave@example.com')
        member = self._mlist.subscribe(dave, MemberRole.member)
        member.preferences.delivery_status = DeliveryStatus.by_user
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('cris@example.com',
                                                     'dave@example.com')))
        # Dave disables his owner membership but re-enables his list
        # membership.  He will not get the owner emails now.
        member.preferences.delivery_status = DeliveryStatus.enabled
        self._dave.preferences.delivery_status = DeliveryStatus.by_user
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('cris@example.com',)))

    def test_all_owners_disabled(self):
        # If all the owners are disabled, then the site owner gets the
        # message.  This prevents a list's -owner address from going into a
        # black hole.
        self._cris.preferences.delivery_status = DeliveryStatus.by_user
        self._dave.preferences.delivery_status = DeliveryStatus.by_user
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('noreply@example.com',)))

    def test_no_owners(self):
        # If a list has no owners or moderators, then the site owner gets the
        # message.  This prevents a list's -owner address from going into a
        # black hole.
        self._cris.unsubscribe()
        self._dave.unsubscribe()
        self.assertEqual(self._mlist.administrators.member_count, 0)
        msgdata = {}
        self._process(self._mlist, self._msg, msgdata)
        self.assertEqual(msgdata['recipients'], set(('noreply@example.com',)))
