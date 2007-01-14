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

"""Password hashing and verification schemes.

Represents passwords using RFC 2307 syntax.
"""

import os
import re
import sha
import hmac

from array import array
from base64 import urlsafe_b64decode as decode
from base64 import urlsafe_b64encode as encode

SALT_LENGTH = 20 # bytes
ITERATIONS  = 2000



class PasswordScheme(object):
    @staticmethod
    def make_secret(password):
        """Return the hashed password""" 
        raise NotImplementedError

    @staticmethod
    def check_response(challenge, response):
        """Return True if response matches challenge.

        It is expected that the scheme specifier prefix is already stripped
        from the response string.
        """
        raise NotImplementedError



class NoPasswordScheme(PasswordScheme):
    @staticmethod
    def make_secret(password):
        return '{NONE}'

    @staticmethod
    def check_response(challenge, response):
        return False



class ClearTextPasswordScheme(PasswordScheme):
    @staticmethod
    def make_secret(password):
        return '{CLEARTEXT}' + password

    @staticmethod
    def check_response(challenge, response):
        return challenge == response



class SHAPasswordScheme(PasswordScheme):
    @staticmethod
    def make_secret(password):
        h = sha.new(password)
        return '{SHA}' + encode(h.digest())

    @staticmethod
    def check_response(challenge, response):
        h = sha.new(response)
        return challenge == encode(h.digest())



class SSHAPasswordScheme(PasswordScheme):
    @staticmethod
    def make_secret(password):
        salt = os.urandom(SALT_LENGTH)
        h = sha.new(password)
        h.update(salt)
        return '{SSHA}' + encode(h.digest() + salt)

    @staticmethod
    def check_response(challenge, response):
        # Get the salt from the challenge
        challenge_bytes = decode(challenge)
        digest = challenge_bytes[:20]
        salt = challenge_bytes[20:]
        h = sha.new(response)
        h.update(salt)
        return digest == h.digest()



# Given by Bob Fleck
class PBKDF2PasswordScheme(PasswordScheme):
    @staticmethod
    def _pbkdf2(password, salt, iterations):
        """From RFC2898 sec. 5.2.  Simplified to handle only 20 byte output
        case.  Output of 20 bytes means always exactly one block to handle,
        and a constant block counter appended to the salt in the initial hmac
        update.
        """
        h = hmac.new(password, None, sha)
        prf = h.copy()
        prf.update(salt + '\x00\x00\x00\x01')
        T = U = array('l', prf.digest())
        while iterations:
            prf = h.copy()
            prf.update(U.tostring())
            U = array('l', prf.digest())
            T = array('l', (t ^ u for t, u in zip(T, U)))
            iterations -= 1
        return T.tostring()

    @staticmethod
    def make_secret(password):
        """From RFC2898 sec. 5.2.  Simplified to handle only 20 byte output
        case.  Output of 20 bytes means always exactly one block to handle,
        and a constant block counter appended to the salt in the initial hmac
        update.
        """
        salt = os.urandom(SALT_LENGTH)
        digest = PBKDF2PasswordScheme._pbkdf2(password, salt, ITERATIONS)
        derived_key = encode(digest + salt)
        return '{PBKDF2 SHA %d}' % ITERATIONS + derived_key

    @staticmethod
    def check_response(challenge, response, prf, iterations):
        # Decode the challenge to get the number of iterations and salt
        # XXX we don't support anything but sha prf
        if prf.lower() <> 'sha':
            return False
        try:
            iterations = int(iterations)
        except (ValueError, TypeError):
            return False
        challenge_bytes = decode(challenge)
        digest = challenge_bytes[:20]
        salt = challenge_bytes[20:]
        key = PBKDF2PasswordScheme._pbkdf2(response, salt, iterations)
        return digest == key



SCHEMES = {
    'none'      : NoPasswordScheme,
    'cleartext' : ClearTextPasswordScheme,
    'sha'       : SHAPasswordScheme,
    'ssha'      : SSHAPasswordScheme,
    'pbkdf2'    : PBKDF2PasswordScheme,
    }


def make_secret(password, scheme):
    scheme_class = SCHEMES.get(scheme.lower(), NoPasswordScheme)
    return scheme_class.make_secret(password)


def check_response(challenge, response):
    mo = re.match(r'{(?P<scheme>[^}]+?)}(?P<rest>.*)',
                  challenge, re.IGNORECASE)
    if not mo:
        return False
    scheme, rest = mo.group('scheme', 'rest')
    scheme_parts = scheme.split()
    scheme_class = SCHEMES.get(scheme_parts[0].lower(), NoPasswordScheme)
    return scheme_class.check_response(rest, response, *scheme_parts[1:])
