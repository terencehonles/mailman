# Copyright (C) 2007-2011 by the Free Software Foundation, Inc.
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

from itertools import izip_longest

from mailman.config import config
from mailman.core import errors
from mailman.testing.layers import ConfigLayer
from mailman.utilities import passwords



class TestPasswordsBase(unittest.TestCase):
    scheme = None

    def setUp(self):
        # passwords; 8-bit or unicode strings; ascii or binary
        self.pw8a       = b'abc'
        self.pw8b       = b'abc\xc3\xbf'     # 'abc\xff'
        self.pwub       = b'abc\xff'
        # bad password; 8-bit or unicode; ascii or binary
        self.bad8a      = b'xyz'
        self.bad8b      = b'xyz\xc3\xbf'     # 'xyz\xff'
        self.badub      = b'xyz\xff'

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



# See itertools doc page examples.
def _grouper(seq):
    args = [iter(seq)] * 2
    return list(izip_longest(*args))


class TestPasswordGeneration(unittest.TestCase):
    layer = ConfigLayer

    def test_default_user_friendly_password_length(self):
        self.assertEqual(len(passwords.make_user_friendly_password()),
                         int(config.passwords.password_length))

    def test_provided_user_friendly_password_length(self):
        self.assertEqual(len(passwords.make_user_friendly_password(12)), 12)

    def test_provided_odd_user_friendly_password_length(self):
        self.assertEqual(len(passwords.make_user_friendly_password(15)), 15)

    def test_user_friendly_password(self):
        password = passwords.make_user_friendly_password()
        for pair in _grouper(password):
            # There will always be one vowel and one non-vowel.
            vowel = (pair[0] if pair[0] in 'aeiou' else pair[1])
            consonant = (pair[0] if pair[0] not in 'aeiou' else pair[1])
            self.assertTrue(vowel in 'aeiou', vowel)
            self.assertTrue(consonant not in 'aeiou', consonant)

    def test_encrypt_password_plaintext_default_scheme(self):
        # Test that a plain text password gets encrypted.
        self.assertEqual(passwords.encrypt_password('abc'),
                         '{CLEARTEXT}abc')

    def test_encrypt_password_plaintext(self):
        # Test that a plain text password gets encrypted with the given scheme.
        scheme = passwords.Schemes.sha
        self.assertEqual(passwords.encrypt_password('abc', scheme),
                         '{SHA}qZk-NkcGgWq6PiVxeFDCbJzQ2J0=')

    def test_encrypt_password_plaintext_by_scheme_name(self):
        # Test that a plain text password gets encrypted with the given
        # scheme, which is given by name.
        self.assertEqual(passwords.encrypt_password('abc', 'cleartext'),
                         '{CLEARTEXT}abc')

    def test_encrypt_password_already_encrypted_default_scheme(self):
        # Test that a password which is already encrypted is return unchanged.
        self.assertEqual(passwords.encrypt_password('{SHA}abc'), '{SHA}abc')

    def test_encrypt_password_already_encrypted(self):
        # Test that a password which is already encrypted is return unchanged,
        # ignoring any requested scheme.
        scheme = passwords.Schemes.cleartext
        self.assertEqual(passwords.encrypt_password('{SHA}abc', scheme),
                         '{SHA}abc')

    def test_encrypt_password_password_value_error(self):
        self.assertRaises(ValueError, passwords.encrypt_password, 7)

    def test_encrypt_password_scheme_value_error(self):
        self.assertRaises(ValueError, passwords.encrypt_password, 'abc', 'foo')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBogusPasswords))
    suite.addTest(unittest.makeSuite(TestNonePasswords))
    suite.addTest(unittest.makeSuite(TestCleartextPasswords))
    suite.addTest(unittest.makeSuite(TestSHAPasswords))
    suite.addTest(unittest.makeSuite(TestSSHAPasswords))
    suite.addTest(unittest.makeSuite(TestPBKDF2Passwords))
    suite.addTest(unittest.makeSuite(TestSchemeLookup))
    suite.addTest(unittest.makeSuite(TestPasswordGeneration))
    return suite
