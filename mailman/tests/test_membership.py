# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""Unit tests for OldStyleMemberships."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import time
import unittest

from mailman import passwords
from mailman.config import config
from mailman.core.errors import NotAMemberError



def password(cleartext):
    return passwords.make_secret(cleartext, passwords.Schemes.ssha)



class TestNoMembers(unittest.TestCase):
    def test_no_member(self):
        eq = self.assertEqual
        raises = self.assertRaises
        mlist = self._mlist
        eq(mlist.getMembers(), [])
        eq(mlist.getRegularMemberKeys(), [])
        eq(mlist.getDigestMemberKeys(), [])
        self.failIf(mlist.isMember('nobody@dom.ain'))
        raises(NotAMemberError, mlist.getMemberKey, 'nobody@dom.ain')
        raises(NotAMemberError, mlist.getMemberCPAddress, 'nobody@dom.ain')
        eq(mlist.getMemberCPAddresses(('nobody@dom.ain', 'noperson@dom.ain')),
           [None, None])
        raises(NotAMemberError, mlist.getMemberPassword, 'nobody@dom.ain')
        raises(NotAMemberError, mlist.authenticateMember,
               'nobody@dom.ain', 'blarg')
        eq(mlist.getMemberLanguage('nobody@dom.ain'), mlist.preferred_language)
        raises(NotAMemberError, mlist.getMemberOption,
               'nobody@dom.ain', config.AcknowledgePosts)
        raises(NotAMemberError, mlist.getMemberName, 'nobody@dom.ain')
        raises(NotAMemberError, mlist.getMemberTopics, 'nobody@dom.ain')
        raises(NotAMemberError, mlist.removeMember, 'nobody@dom.ain')

    def test_add_member_mixed_case(self):
        eq = self.assertEqual
        mlist = self._mlist
        mlist.addNewMember('APerson@dom.AIN')
        eq(mlist.getMembers(), ['aperson@dom.ain'])
        eq(mlist.getRegularMemberKeys(), ['aperson@dom.ain'])
        self.failUnless(mlist.isMember('APerson@dom.AIN'))
        self.failUnless(mlist.isMember('aperson@dom.ain'))
        self.failUnless(mlist.isMember('APERSON@DOM.AIN'))
        eq(mlist.getMemberCPAddress('aperson@dom.ain'), 'APerson@dom.AIN')
        eq(mlist.getMemberCPAddress('APerson@dom.ain'), 'APerson@dom.AIN')
        eq(mlist.getMemberCPAddress('APERSON@DOM.AIN'), 'APerson@dom.AIN')
        eq(mlist.getMemberCPAddresses(('aperson@dom.ain',)),
           ['APerson@dom.AIN'])
        eq(mlist.getMemberCPAddresses(('APerson@dom.ain',)),
           ['APerson@dom.AIN'])
        eq(mlist.getMemberCPAddresses(('APERSON@DOM.AIN',)),
           ['APerson@dom.AIN'])



class TestMembers(unittest.TestCase):
    def setUp(self):
        self._member_password = password('xxXXxx')
        self._mlist.addNewMember('person@dom.ain',
                                 digest=0,
                                 password=self._member_password,
                                 language='xx',
                                 realname='A. Nice Person')

    def test_add_member(self):
        eq = self.assertEqual
        mlist = self._mlist
        eq(mlist.getMembers(), ['person@dom.ain'])
        eq(mlist.getRegularMemberKeys(), ['person@dom.ain'])
        eq(mlist.getDigestMemberKeys(), [])
        self.failUnless(mlist.isMember('person@dom.ain'))
        eq(mlist.getMemberKey('person@dom.ain'), 'person@dom.ain')
        eq(mlist.getMemberCPAddress('person@dom.ain'), 'person@dom.ain')
        eq(mlist.getMemberCPAddresses(('person@dom.ain', 'noperson@dom.ain')),
           ['person@dom.ain', None])
        eq(mlist.getMemberPassword('person@dom.ain'), self._member_password)
        eq(mlist.getMemberLanguage('person@dom.ain'), 'en')
        eq(mlist.getMemberOption('person@dom.ain', config.Digests), 0)
        eq(mlist.getMemberOption('person@dom.ain', config.AcknowledgePosts), 0)
        eq(mlist.getMemberName('person@dom.ain'), 'A. Nice Person')
        eq(mlist.getMemberTopics('person@dom.ain'), [])

    def test_authentication(self):
        mlist = self._mlist
        self.failIf(mlist.authenticateMember('person@dom.ain', 'xxx'))
        self.assertEqual(mlist.authenticateMember('person@dom.ain', 'xxXXxx'),
                         self._member_password)

    def test_remove_member(self):
        eq = self.assertEqual
        raises = self.assertRaises
        mlist = self._mlist
        mlist.removeMember('person@dom.ain')
        eq(mlist.getMembers(), [])
        eq(mlist.getRegularMemberKeys(), [])
        eq(mlist.getDigestMemberKeys(), [])
        self.failIf(mlist.isMember('person@dom.ain'))
        raises(NotAMemberError, mlist.getMemberKey, 'person@dom.ain')
        raises(NotAMemberError, mlist.getMemberCPAddress, 'person@dom.ain')
        eq(mlist.getMemberCPAddresses(('person@dom.ain', 'noperson@dom.ain')),
           [None, None])
        raises(NotAMemberError, mlist.getMemberPassword, 'person@dom.ain')
        raises(NotAMemberError, mlist.authenticateMember,
               'person@dom.ain', 'blarg')
        eq(mlist.getMemberLanguage('person@dom.ain'), mlist.preferred_language)
        raises(NotAMemberError, mlist.getMemberOption,
               'person@dom.ain', config.AcknowledgePosts)
        raises(NotAMemberError, mlist.getMemberName, 'person@dom.ain')
        raises(NotAMemberError, mlist.getMemberTopics, 'person@dom.ain')

    def test_remove_member_clears(self):
        eq = self.assertEqual
        raises = self.assertRaises
        # We don't really care what the bounce info is
        class Info:
            pass
        info = Info()
        mlist = self._mlist
        mlist.setBounceInfo('person@dom.ain', info)
        mlist.setDeliveryStatus('person@dom.ain', MemberAdaptor.BYADMIN)
        mlist.removeMember('person@dom.ain')
        raises(NotAMemberError, mlist.getDeliveryStatus, 'person@dom.ain')
        raises(NotAMemberError, mlist.getDeliveryStatusChangeTime,
               'person@dom.ain')
        raises(NotAMemberError, mlist.getBounceInfo, 'person@dom.ain')
        eq(mlist.getDeliveryStatusMembers(), [])
        eq(mlist.getBouncingMembers(), [])

    def test_change_address(self):
        eq = self.assertEqual
        raises = self.assertRaises
        mlist = self._mlist
        mlist.changeMemberAddress('person@dom.ain', 'nice@dom.ain')
        # Check the new address
        eq(mlist.getMembers(), ['nice@dom.ain'])
        eq(mlist.getRegularMemberKeys(), ['nice@dom.ain'])
        eq(mlist.getDigestMemberKeys(), [])
        self.failUnless(mlist.isMember('nice@dom.ain'))
        eq(mlist.getMemberKey('nice@dom.ain'), 'nice@dom.ain')
        eq(mlist.getMemberCPAddress('nice@dom.ain'), 'nice@dom.ain')
        eq(mlist.getMemberCPAddresses(('nice@dom.ain', 'nonice@dom.ain')),
           ['nice@dom.ain', None])
        eq(mlist.getMemberPassword('nice@dom.ain'), self._member_password)
        eq(mlist.getMemberLanguage('nice@dom.ain'), 'en')
        eq(mlist.getMemberOption('nice@dom.ain', config.Digests), 0)
        eq(mlist.getMemberOption('nice@dom.ain', config.AcknowledgePosts), 0)
        eq(mlist.getMemberName('nice@dom.ain'), 'A. Nice Person')
        eq(mlist.getMemberTopics('nice@dom.ain'), [])
        # Check the old address
        eq(mlist.getMembers(), ['nice@dom.ain'])
        eq(mlist.getRegularMemberKeys(), ['nice@dom.ain'])
        eq(mlist.getDigestMemberKeys(), [])
        self.failIf(mlist.isMember('person@dom.ain'))
        raises(NotAMemberError, mlist.getMemberKey, 'person@dom.ain')
        raises(NotAMemberError, mlist.getMemberCPAddress, 'person@dom.ain')
        eq(mlist.getMemberCPAddresses(('person@dom.ain', 'noperson@dom.ain')),
           [None, None])
        raises(NotAMemberError, mlist.getMemberPassword, 'person@dom.ain')
        raises(NotAMemberError, mlist.authenticateMember,
               'person@dom.ain', 'blarg')
        eq(mlist.getMemberLanguage('person@dom.ain'), mlist.preferred_language)
        raises(NotAMemberError, mlist.getMemberOption,
               'person@dom.ain', config.AcknowledgePosts)
        raises(NotAMemberError, mlist.getMemberName, 'person@dom.ain')
        raises(NotAMemberError, mlist.getMemberTopics, 'person@dom.ain')

    def test_set_password(self):
        eq = self.assertEqual
        mlist = self._mlist
        new_password = password('yyYYyy')
        mlist.setMemberPassword('person@dom.ain', new_password)
        eq(mlist.getMemberPassword('person@dom.ain'), new_password)
        eq(mlist.authenticateMember('person@dom.ain', 'yyYYyy'), new_password)
        self.failIf(mlist.authenticateMember('person@dom.ain', 'xxXXxx'))

    def test_set_language(self):
        # This test requires that the 'xx' language be in the global
        # config.LC_DESCRIPTIONS.  Save that value and be sure to restore it
        # after the test is done.
        odesc = config.LC_DESCRIPTIONS.copy()
        try:
            config.add_language('xx', 'Xxian', 'utf-8')
            self._mlist.add_language('xx')
            self._mlist.setMemberLanguage('person@dom.ain', 'xx')
            self.assertEqual(self._mlist.getMemberLanguage('person@dom.ain'),
                             'xx')
        finally:
            config.LC_DESCRIPTIONS = odesc

    def test_basic_option(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        # First test the current option values
        eq(gmo('person@dom.ain', config.Digests), 0)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 0)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 0)
        eq(gmo('person@dom.ain', config.DisableMime), 0)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 0)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 0)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 0)

    def test_set_digests(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        self._mlist.setMemberOption('person@dom.ain', config.Digests, 1)
        eq(gmo('person@dom.ain', config.Digests), 1)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 0)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 0)
        eq(gmo('person@dom.ain', config.DisableMime), 0)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 0)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 0)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 0)

    def test_set_disable_delivery(self):
        eq = self.assertEqual
        gds = self._mlist.getDeliveryStatus
        eq(gds('person@dom.ain'), MemberAdaptor.ENABLED)
        self._mlist.setDeliveryStatus('person@dom.ain', MemberAdaptor.UNKNOWN)
        eq(gds('person@dom.ain'), MemberAdaptor.UNKNOWN)
        self._mlist.setDeliveryStatus('person@dom.ain', MemberAdaptor.BYUSER)
        eq(gds('person@dom.ain'), MemberAdaptor.BYUSER)
        self._mlist.setDeliveryStatus('person@dom.ain', MemberAdaptor.BYBOUNCE)
        eq(gds('person@dom.ain'), MemberAdaptor.BYBOUNCE)
        self._mlist.setDeliveryStatus('person@dom.ain', MemberAdaptor.BYADMIN)
        eq(gds('person@dom.ain'), MemberAdaptor.BYADMIN)

    def test_delivery_status_time(self):
        now = time.time()
        time.sleep(1)
        self._mlist.setDeliveryStatus('person@dom.ain', MemberAdaptor.BYUSER)
        self.failUnless(
            self._mlist.getDeliveryStatusChangeTime('person@dom.ain')
            > now)
        self._mlist.setDeliveryStatus('person@dom.ain', MemberAdaptor.ENABLED)
        self.assertEqual(
            self._mlist.getDeliveryStatusChangeTime('person@dom.ain'),
            0)

    def test_set_dont_receive_own_posts(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        self._mlist.setMemberOption('person@dom.ain',
                                    config.DontReceiveOwnPosts, 1)
        eq(gmo('person@dom.ain', config.Digests), 0)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 1)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 0)
        eq(gmo('person@dom.ain', config.DisableMime), 0)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 0)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 0)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 0)

    def test_set_acknowledge_posts(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        self._mlist.setMemberOption('person@dom.ain',
                                    config.AcknowledgePosts, 1)
        eq(gmo('person@dom.ain', config.Digests), 0)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 0)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 1)
        eq(gmo('person@dom.ain', config.DisableMime), 0)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 0)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 0)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 0)

    def test_disable_mime(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        self._mlist.setMemberOption('person@dom.ain',
                                    config.DisableMime, 1)
        eq(gmo('person@dom.ain', config.Digests), 0)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 0)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 0)
        eq(gmo('person@dom.ain', config.DisableMime), 1)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 0)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 0)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 0)

    def test_conceal_subscription(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        self._mlist.setMemberOption('person@dom.ain',
                                    config.ConcealSubscription, 1)
        eq(gmo('person@dom.ain', config.Digests), 0)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 0)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 0)
        eq(gmo('person@dom.ain', config.DisableMime), 0)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 1)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 0)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 0)

    def test_suppress_password_reminder(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        self._mlist.setMemberOption('person@dom.ain',
                                    config.SuppressPasswordReminder, 1)
        eq(gmo('person@dom.ain', config.Digests), 0)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 0)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 0)
        eq(gmo('person@dom.ain', config.DisableMime), 0)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 0)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 1)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 0)

    def test_receive_nonmatching_topics(self):
        eq = self.assertEqual
        gmo = self._mlist.getMemberOption
        self._mlist.setMemberOption('person@dom.ain',
                                    config.ReceiveNonmatchingTopics, 1)
        eq(gmo('person@dom.ain', config.Digests), 0)
        eq(gmo('person@dom.ain', config.DontReceiveOwnPosts), 0)
        eq(gmo('person@dom.ain', config.AcknowledgePosts), 0)
        eq(gmo('person@dom.ain', config.DisableMime), 0)
        eq(gmo('person@dom.ain', config.ConcealSubscription), 0)
        eq(gmo('person@dom.ain', config.SuppressPasswordReminder), 0)
        eq(gmo('person@dom.ain', config.ReceiveNonmatchingTopics), 1)

    def test_member_name(self):
        self._mlist.setMemberName('person@dom.ain', 'A. Good Person')
        self.assertEqual(self._mlist.getMemberName('person@dom.ain'),
                         'A. Good Person')

    def test_member_topics(self):
        eq = self.assertEqual
        mlist = self._mlist
        mlist.setMemberTopics('person@dom.ain', ['topic1', 'topic2', 'topic3'])
        eq(mlist.getMemberTopics('person@dom.ain'),
                                 ['topic1', 'topic2', 'topic3'])
        mlist.setMemberTopics('person@dom.ain', None)
        eq(mlist.getMemberTopics('person@dom.ain'), [])

    def test_bounce_info(self):
        eq = self.assertEqual
        mlist = self._mlist
        # We don't really care what info is stored
        class Info: pass
        info = Info()
        # Test setting and getting
        mlist.setBounceInfo('person@dom.ain', info)
        eq(mlist.getBounceInfo('person@dom.ain'), info)
        # Test case sensitivity
        eq(mlist.getBounceInfo('PERSON@dom.ain'), info)
        info2 = Info()
        mlist.setBounceInfo('PeRsOn@dom.ain', info2)
        eq(mlist.getBounceInfo('person@dom.ain'), info2)
        eq(mlist.getBounceInfo('PeRsOn@dom.ain'), info2)
        eq(mlist.getBounceInfo('PERSON@DOM.AIN'), info2)
        # Test getBouncingMembers...
        eq(mlist.getBouncingMembers(), ['person@dom.ain'])
        # Test clearing bounce information...
        mlist.setBounceInfo('person@dom.ain', None)
        eq(mlist.getBouncingMembers(), [])
        eq(mlist.getBounceInfo('person@dom.ain'), None)
        # Make sure that you can clear the attributes case insensitively
        mlist.setBounceInfo('person@dom.ain', info)
        mlist.setBounceInfo('PERSON@dom.ain', None)
        eq(mlist.getBouncingMembers(), [])



def test_suite():
    suite = unittest.TestSuite()
    return suite
