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

"""Unit tests for the passwords module."""

import unittest

from Mailman import passwords



class TestPasswordsBase(unittest.TestCase):
    scheme = None

    def setUp(self):
        # passwords; 8-bit or unicode strings; ascii or binary
        self.pw8a       = 'abc'
        self.pwua       = u'abc'
        self.pw8b       = 'abc\xc3\xbf'     # 'abc\xff'
        self.pwub       = u'abc\xff'
        # bad password; 8-bit or unicode; ascii or binary
        self.bad8a      = 'xyz'
        self.badua      = u'xyz'
        self.bad8b      = 'xyz\xc3\xbf'     # 'xyz\xff'
        self.badub      = u'xyz\xff'

    def test_passwords(self):
        unless = self.failUnless
        failif = self.failIf
        secret = passwords.make_secret(self.pw8a, self.scheme)
        unless(passwords.check_response(secret, self.pw8a))
        failif(passwords.check_response(secret, self.bad8a))

    def test_unicode_passwords(self):
        unless = self.failUnless
        failif = self.failIf
        secret = passwords.make_secret(self.pwua, self.scheme)
        unless(passwords.check_response(secret, self.pwua))
        failif(passwords.check_response(secret, self.badua))

    def test_passwords_with_funky_chars(self):
        unless = self.failUnless
        failif = self.failIf
        secret = passwords.make_secret(self.pw8b, self.scheme)
        unless(passwords.check_response(secret, self.pw8b))
        failif(passwords.check_response(secret, self.bad8b))

    def test_unicode_passwords_with_funky_chars(self):
        unless = self.failUnless
        failif = self.failIf
        secret = passwords.make_secret(self.pwub, self.scheme)
        unless(passwords.check_response(secret, self.pwub))
        failif(passwords.check_response(secret, self.badub))



class TestBogusPasswords(TestPasswordsBase):
    scheme = -1

    def test_passwords(self):
        failif = self.failIf
        secret = passwords.make_secret(self.pw8a, self.scheme)
        failif(passwords.check_response(secret, self.pw8a))
        failif(passwords.check_response(secret, self.bad8a))

    def test_unicode_passwords(self):
        failif = self.failIf
        secret = passwords.make_secret(self.pwua, self.scheme)
        failif(passwords.check_response(secret, self.pwua))
        failif(passwords.check_response(secret, self.badua))

    def test_passwords_with_funky_chars(self):
        failif = self.failIf
        secret = passwords.make_secret(self.pw8b, self.scheme)
        failif(passwords.check_response(secret, self.pw8b))
        failif(passwords.check_response(secret, self.bad8b))

    def test_unicode_passwords_with_funky_chars(self):
        failif = self.failIf
        secret = passwords.make_secret(self.pwub, self.scheme)
        failif(passwords.check_response(secret, self.pwub))
        failif(passwords.check_response(secret, self.badub))



class TestNonePasswords(TestBogusPasswords):
    scheme = 'no_scheme'


class TestCleartextPasswords(TestPasswordsBase):
    scheme = 'cleartext'


class TestSHAPasswords(TestPasswordsBase):
    scheme = 'sha'


class TestSSHAPasswords(TestPasswordsBase):
    scheme = 'ssha'


class TestPBKDF2Passwords(TestPasswordsBase):
    scheme = 'pbkdf2'



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBogusPasswords))
    suite.addTest(unittest.makeSuite(TestNonePasswords))
    suite.addTest(unittest.makeSuite(TestCleartextPasswords))
    suite.addTest(unittest.makeSuite(TestSHAPasswords))
    suite.addTest(unittest.makeSuite(TestSSHAPasswords))
    suite.addTest(unittest.makeSuite(TestPBKDF2Passwords))
    return suite
