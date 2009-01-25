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

"""Unit tests for the SecurityManager module."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import os
import errno
import unittest

# Don't use cStringIO because we're going to inherit
from StringIO import StringIO

from mailman import Utils
from mailman import passwords
from mailman.config import config



def password(cleartext):
    return passwords.make_secret(cleartext, passwords.Schemes.ssha)



class TestSecurityManager(unittest.TestCase):
    def test_init_vars(self):
        eq = self.assertEqual
        eq(self._mlist.mod_password, None)
        eq(self._mlist.passwords, {})

    def test_auth_context_info_authuser(self):
        mlist = self._mlist
        self.assertRaises(TypeError, mlist.AuthContextInfo, config.AuthUser)
        # Add a member
        mlist.addNewMember('aperson@dom.ain', password='xxXXxx')
        self.assertEqual(
            mlist.AuthContextInfo(config.AuthUser, 'aperson@dom.ain'),
            ('_xtest%40example.com+user+aperson--at--dom.ain', 'xxXXxx'))

    def test_auth_context_moderator(self):
        mlist = self._mlist
        mlist.mod_password = 'yyYYyy'
        self.assertEqual(
            mlist.AuthContextInfo(config.AuthListModerator),
            ('_xtest%40example.com+moderator', 'yyYYyy'))

    def test_auth_context_admin(self):
        mlist = self._mlist
        mlist.password = 'zzZZzz'
        self.assertEqual(
            mlist.AuthContextInfo(config.AuthListAdmin),
            ('_xtest%40example.com+admin', 'zzZZzz'))

    def test_auth_context_site(self):
        mlist = self._mlist
        mlist.password = 'aaAAaa'
        self.assertEqual(
            mlist.AuthContextInfo(config.AuthSiteAdmin),
            ('_xtest%40example.com+admin', 'aaAAaa'))

    def test_auth_context_huh(self):
        self.assertEqual(
            self._mlist.AuthContextInfo('foo'),
            (None, None))



class TestAuthenticate(unittest.TestCase):
    def setUp(self):
        Utils.set_global_password('bbBBbb', siteadmin=True)
        Utils.set_global_password('ccCCcc', siteadmin=False)

    def tearDown(self):
        try:
            os.unlink(config.SITE_PW_FILE)
        except OSError, e:
            if e.errno <> errno.ENOENT:
                raise
        try:
            os.unlink(config.LISTCREATOR_PW_FILE)
        except OSError, e:
            if e.errno <> errno.ENOENT:
                raise

    def test_auth_creator(self):
        self.assertEqual(self._mlist.Authenticate(
            [config.AuthCreator], 'ccCCcc'), config.AuthCreator)

    def test_auth_creator_unauth(self):
        self.assertEqual(self._mlist.Authenticate(
            [config.AuthCreator], 'xxxxxx'), config.UnAuthorized)

    def test_auth_site_admin(self):
        self.assertEqual(self._mlist.Authenticate(
            [config.AuthSiteAdmin], 'bbBBbb'), config.AuthSiteAdmin)

    def test_auth_site_admin_unauth(self):
        self.assertEqual(self._mlist.Authenticate(
            [config.AuthSiteAdmin], 'xxxxxx'), config.UnAuthorized)

    def test_list_admin(self):
        self._mlist.password = password('ttTTtt')
        self.assertEqual(self._mlist.Authenticate(
            [config.AuthListAdmin], 'ttTTtt'), config.AuthListAdmin)

    def test_list_admin_unauth(self):
        self._mlist.password = password('ttTTtt')
        self.assertEqual(self._mlist.Authenticate(
            [config.AuthListAdmin], 'xxxxxx'), config.UnAuthorized)

    def test_list_moderator(self):
        self._mlist.mod_password = password('mmMMmm')
        self.assertEqual(self._mlist.Authenticate(
            [config.AuthListModerator], 'mmMMmm'), config.AuthListModerator)

    def test_user(self):
        mlist = self._mlist
        mlist.addNewMember('aperson@dom.ain', password=password('nosrepa'))
        self.assertEqual(mlist.Authenticate(
            [config.AuthUser], 'nosrepa', 'aperson@dom.ain'), config.AuthUser)

    def test_wrong_user(self):
        mlist = self._mlist
        mlist.addNewMember('aperson@dom.ain', password='nosrepa')
        self.assertEqual(
            mlist.Authenticate([config.AuthUser], 'nosrepa', 'bperson@dom.ain'),
            config.UnAuthorized)

    def test_no_user(self):
        mlist = self._mlist
        mlist.addNewMember('aperson@dom.ain', password='nosrepa')
        self.assertEqual(mlist.Authenticate([config.AuthUser], 'norespa'),
                         config.UnAuthorized)

    def test_user_unauth(self):
        mlist = self._mlist
        mlist.addNewMember('aperson@dom.ain', password='nosrepa')
        self.assertEqual(mlist.Authenticate(
            [config.AuthUser], 'xxxxxx', 'aperson@dom.ain'),
                         config.UnAuthorized)

    def test_value_error(self):
        self.assertRaises(ValueError, self._mlist.Authenticate,
                          ['spooge'], 'xxxxxx', 'zperson@dom.ain')



class StripperIO(StringIO):
    HEAD = 'Set-Cookie: '
    def write(self, s):
        if s.startswith(self.HEAD):
            s = s[len(self.HEAD):]
        StringIO.write(self, s)


class TestWebAuthenticate(unittest.TestCase):
    def setUp(self):
        Utils.set_global_password('bbBBbb', siteadmin=True)
        Utils.set_global_password('ccCCcc', siteadmin=False)
        mlist = self._mlist
        mlist.mod_password = password('abcdefg')
        mlist.addNewMember('aperson@dom.ain', password='qqQQqq')
        # Set up the cookie data
        sfp = StripperIO()
        print >> sfp, mlist.MakeCookie(config.AuthSiteAdmin)
        # AuthCreator isn't handled in AuthContextInfo()
        print >> sfp, mlist.MakeCookie(config.AuthListAdmin)
        print >> sfp, mlist.MakeCookie(config.AuthListModerator)
        print >> sfp, mlist.MakeCookie(config.AuthUser, 'aperson@dom.ain')
        # Strip off the "Set-Cookie: " prefix
        cookie = sfp.getvalue()
        os.environ['HTTP_COOKIE'] = cookie

    def tearDown(self):
        try:
            os.unlink(config.SITE_PW_FILE)
        except OSError, e:
            if e.errno <> errno.ENOENT:
                raise
        try:
            os.unlink(config.LISTCREATOR_PW_FILE)
        except OSError, e:
            if e.errno <> errno.ENOENT:
                raise
        del os.environ['HTTP_COOKIE']

    def test_auth_site_admin(self):
        self.failUnless(self._mlist.WebAuthenticate(
            [config.AuthSiteAdmin], 'does not matter'))

    def test_list_admin(self):
        self.failUnless(self._mlist.WebAuthenticate(
            [config.AuthListAdmin], 'does not matter'))

    def test_list_moderator(self):
        self.failUnless(self._mlist.WebAuthenticate(
            [config.AuthListModerator], 'does not matter'))

    def test_user(self):
        self.failUnless(self._mlist.WebAuthenticate(
            [config.AuthUser], 'does not matter'))

    def test_not_a_user(self):
        self._mlist.removeMember('aperson@dom.ain')
        self.failIf(self._mlist.WebAuthenticate(
            [config.AuthUser], 'does not matter', 'aperson@dom.ain'))



# TBD: Tests for MakeCookie(), ZapCookie(), CheckCookie() -- although the
# latter is implicitly tested by testing WebAuthenticate() above.



def test_suite():
    suite = unittest.TestSuite()
##     suite.addTest(unittest.makeSuite(TestSecurityManager))
##     suite.addTest(unittest.makeSuite(TestAuthenticate))
##     suite.addTest(unittest.makeSuite(TestWebAuthenticate))
    return suite
