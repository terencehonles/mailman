# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""Unit tests for the passwords module."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from mailman import passwords
from mailman.core import errors



class TestPasswordsBase(unittest.TestCase):
    scheme = None

    def setUp(self):
        # passwords; 8-bit or unicode strings; ascii or binary
        self.pw8a       = 'abc'
        self.pw8b       = 'abc\xc3\xbf'     # 'abc\xff'
        self.pwub       = 'abc\xff'
        # bad password; 8-bit or unicode; ascii or binary
        self.bad8a      = 'xyz'
        self.bad8b      = 'xyz\xc3\xbf'     # 'xyz\xff'
        self.badub      = 'xyz\xff'

    def test_passwords(self):
        unless = self.failUnless
        failif = self.failIf
        secret = passwords.make_secret(self.pw8a, self.scheme)
        unless(passwords.check_response(secret, self.pw8a))
        failif(passwords.check_response(secret, self.bad8a))

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
        self.assertRaises(errors.BadPasswordSchemeError,
                          passwords.make_secret, self.pw8a, self.scheme)

    def test_passwords_with_funky_chars(self):
        self.assertRaises(errors.BadPasswordSchemeError,
                          passwords.make_secret, self.pw8b, self.scheme)

    def test_unicode_passwords_with_funky_chars(self):
        self.assertRaises(errors.BadPasswordSchemeError,
                          passwords.make_secret, self.pwub, self.scheme)



class TestNonePasswords(TestPasswordsBase):
    scheme = passwords.Schemes.no_scheme

    def test_passwords(self):
        failif = self.failIf
        secret = passwords.make_secret(self.pw8a, self.scheme)
        failif(passwords.check_response(secret, self.pw8a))
        failif(passwords.check_response(secret, self.bad8a))

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



class TestCleartextPasswords(TestPasswordsBase):
    scheme = passwords.Schemes.cleartext


class TestSHAPasswords(TestPasswordsBase):
    scheme = passwords.Schemes.sha


class TestSSHAPasswords(TestPasswordsBase):
    scheme = passwords.Schemes.ssha


class TestPBKDF2Passwords(TestPasswordsBase):
    scheme = passwords.Schemes.pbkdf2



class TestSchemeLookup(unittest.TestCase):
    def test_scheme_name_lookup(self):
        unless = self.failUnless
        unless(passwords.lookup_scheme('NONE') is passwords.Schemes.no_scheme)
        unless(passwords.lookup_scheme('CLEARTEXT') is
               passwords.Schemes.cleartext)
        unless(passwords.lookup_scheme('SHA') is passwords.Schemes.sha)
        unless(passwords.lookup_scheme('SSHA') is passwords.Schemes.ssha)
        unless(passwords.lookup_scheme('PBKDF2') is passwords.Schemes.pbkdf2)
        unless(passwords.lookup_scheme(' -bogus- ') is None)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBogusPasswords))
    suite.addTest(unittest.makeSuite(TestNonePasswords))
    suite.addTest(unittest.makeSuite(TestCleartextPasswords))
    suite.addTest(unittest.makeSuite(TestSHAPasswords))
    suite.addTest(unittest.makeSuite(TestSSHAPasswords))
    suite.addTest(unittest.makeSuite(TestPBKDF2Passwords))
    suite.addTest(unittest.makeSuite(TestSchemeLookup))
    return suite
