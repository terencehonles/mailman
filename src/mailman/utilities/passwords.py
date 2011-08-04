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

"""Password hashing and verification schemes.

Represents passwords using RFC 2307 syntax (as best we can tell).
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Schemes',
    'check_response',
    'encrypt_password',
    'make_secret',
    'make_user_friendly_password',
    ]


import os
import re
import hmac
import random
import hashlib

from array import array
from base64 import urlsafe_b64decode as decode
from base64 import urlsafe_b64encode as encode
from flufl.enum import Enum
from itertools import chain, product
from string import ascii_lowercase

from mailman.config import config
from mailman.core import errors

SALT_LENGTH = 20 # bytes
ITERATIONS  = 2000
EMPTYSTRING = ''
SCHEME_RE = r'{(?P<scheme>[^}]+?)}(?P<rest>.*)'



class PasswordScheme:
    """Password scheme base class."""
    TAG = b''

    @staticmethod
    def make_secret(password):
        """Return the hashed password.

        :param password: The clear text password.
        :type password: string
        :return: The encrypted password.
        :rtype: string
        """
        raise NotImplementedError

    @staticmethod
    def check_response(challenge, response):
        """Check a response against a challenge.

        It is expected that the scheme specifier prefix is already stripped
        from the response string.

        :param challenge: The challenge.
        :type challenge: string
        :param response: The response.
        :type response: string
        :return: True if the response matches the challenge.
        :rtype: bool
        """
        raise NotImplementedError



class NoPasswordScheme(PasswordScheme):
    """A password scheme without passwords."""

    TAG = b'NONE'

    @staticmethod
    def make_secret(password):
        """See `PasswordScheme`."""
        return b''

    @staticmethod
    def check_response(challenge, response):
        """See `PasswordScheme`."""
        return False



class ClearTextPasswordScheme(PasswordScheme):
    """A password scheme that stores clear text passwords."""

    TAG = b'CLEARTEXT'

    @staticmethod
    def make_secret(password):
        """See `PasswordScheme`."""
        return password

    @staticmethod
    def check_response(challenge, response):
        """See `PasswordScheme`."""
        return challenge == response



class SHAPasswordScheme(PasswordScheme):
    """A password scheme that encodes the password using SHA1."""

    TAG = b'SHA'

    @staticmethod
    def make_secret(password):
        """See `PasswordScheme`."""
        h = hashlib.sha1(password)
        return encode(h.digest())

    @staticmethod
    def check_response(challenge, response):
        """See `PasswordScheme`."""
        h = hashlib.sha1(response)
        return challenge == encode(h.digest())



class SSHAPasswordScheme(PasswordScheme):
    """A password scheme that encodes the password using salted SHA1."""

    TAG = b'SSHA'

    @staticmethod
    def make_secret(password):
        """See `PasswordScheme`."""
        salt = os.urandom(SALT_LENGTH)
        h = hashlib.sha1(password)
        h.update(salt)
        return encode(h.digest() + salt)

    @staticmethod
    def check_response(challenge, response):
        """See `PasswordScheme`."""
        # Get the salt from the challenge
        challenge_bytes = decode(challenge)
        digest = challenge_bytes[:20]
        salt = challenge_bytes[20:]
        h = hashlib.sha1(response)
        h.update(salt)
        return digest == h.digest()



# Basic algorithm given by Bob Fleck
class PBKDF2PasswordScheme(PasswordScheme):
    """RFC 2989 password encoding scheme."""

    # This is a bit nasty if we wanted a different prf or iterations.  OTOH,
    # we really have no clue what the standard LDAP-ish specification for
    # those options is.
    TAG = b'PBKDF2 SHA {0}'.format(ITERATIONS)

    @staticmethod
    def _pbkdf2(password, salt, iterations):
        """From RFC2898 sec. 5.2.  Simplified to handle only 20 byte output
        case.  Output of 20 bytes means always exactly one block to handle,
        and a constant block counter appended to the salt in the initial hmac
        update.
        """
        h = hmac.new(password, None, hashlib.sha1)
        prf = h.copy()
        prf.update(salt + b'\x00\x00\x00\x01')
        T = U = array(b'i', prf.digest())
        while iterations:
            prf = h.copy()
            prf.update(U.tostring())
            U = array(b'i', prf.digest())
            T = array(b'i', (t ^ u for t, u in zip(T, U)))
            iterations -= 1
        return T.tostring()

    @staticmethod
    def make_secret(password):
        """See `PasswordScheme`.

        From RFC2898 sec. 5.2.  Simplified to handle only 20 byte output
        case.  Output of 20 bytes means always exactly one block to handle,
        and a constant block counter appended to the salt in the initial hmac
        update.
        """
        salt = os.urandom(SALT_LENGTH)
        digest = PBKDF2PasswordScheme._pbkdf2(password, salt, ITERATIONS)
        derived_key = encode(digest + salt)
        return derived_key

    @staticmethod
    def check_response(challenge, response, prf, iterations):
        """See `PasswordScheme`."""
        # Decode the challenge to get the number of iterations and salt.  We
        # don't support anything but SHA PRF.
        if prf.lower() != b'sha':
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



class Schemes(Enum):
    """List of password schemes."""
    # no_scheme is deliberately ugly because no one should be using it.  Yes,
    # this makes cleartext inconsistent, but that's a common enough
    # terminology to justify the missing underscore.
    no_scheme   = 1
    cleartext   = 2
    sha         = 3
    ssha        = 4
    pbkdf2      = 5


_SCHEMES_BY_ENUM = {
    Schemes.no_scheme   : NoPasswordScheme,
    Schemes.cleartext   : ClearTextPasswordScheme,
    Schemes.sha         : SHAPasswordScheme,
    Schemes.ssha        : SSHAPasswordScheme,
    Schemes.pbkdf2      : PBKDF2PasswordScheme,
    }


# Some scheme tags have arguments, but the key for this dictionary should just
# be the lowercased scheme name.
_SCHEMES_BY_TAG = dict((_SCHEMES_BY_ENUM[e].TAG.split(' ')[0].lower(), e)
                       for e in _SCHEMES_BY_ENUM)

_DEFAULT_SCHEME = NoPasswordScheme



def make_secret(password, scheme=None):
    """Encrypt a password.

    :param password: The clear text password.
    :type password: string
    :param scheme: The password scheme name.
    :type scheme: string
    :return: The encrypted password.
    :rtype: string
    """
    # The hash algorithms operate on bytes not strings.  The password argument
    # as provided here by the client will be a string (in Python 2 either
    # unicode or 8-bit, in Python 3 always unicode).  We need to encode this
    # string into a byte array, and the way to spell that in Python 2 is to
    # encode the string to utf-8.  The returned secret is a string, so it must
    # be a unicode.
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    scheme_class = _SCHEMES_BY_ENUM.get(scheme)
    if not scheme_class:
        raise errors.BadPasswordSchemeError(scheme)
    secret = scheme_class.make_secret(password)
    return b'{{{0}}}{1}'.format(scheme_class.TAG, secret)


def check_response(challenge, response):
    """Check a response against a challenge.

    :param challenge: The challenge.
    :type challenge: string
    :param response: The response.
    :type response: string
    :return: True if the response matches the challenge.
    :rtype: bool
    """
    mo = re.match(SCHEME_RE, challenge, re.IGNORECASE)
    if not mo:
        return False
    # See above for why we convert here.  However because we should have
    # generated the challenge, we assume that it is already a byte string.
    if isinstance(response, unicode):
        response = response.encode('utf-8')
    scheme_group, rest_group = mo.group('scheme', 'rest')
    scheme_parts = scheme_group.split()
    scheme       = scheme_parts[0].lower()
    scheme_enum  = _SCHEMES_BY_TAG.get(scheme, _DEFAULT_SCHEME)
    scheme_class = _SCHEMES_BY_ENUM[scheme_enum]
    if isinstance(rest_group, unicode):
        rest_group = rest_group.encode('utf-8')
    return scheme_class.check_response(rest_group, response, *scheme_parts[1:])


def lookup_scheme(scheme_name):
    """Look up a password scheme.

    :param scheme_name: The password scheme name.
    :type scheme_name: string
    :return: Password scheme class.
    :rtype: `PasswordScheme`
    """
    return _SCHEMES_BY_TAG.get(scheme_name.lower())


def encrypt_password(password, scheme=None):
    """Return an encrypted password.

    If the given password is already encrypted (i.e. it has a scheme prefix),
    then the password is return unchanged.  Otherwise, it is encrypted with
    the given scheme or the default scheme.

    :param password: The plain text or encrypted password.
    :type password: string
    :param scheme: The scheme enum to use for encryption.  If not given, the
        system default scheme is used.  This can be a `Schemes` enum item, or
        the scheme name as a string.
    :type scheme: `Schemes` enum, or string.
    :return: The encrypted password.
    :rtype: bytes
    """
    if not isinstance(password, (bytes, unicode)):
        raise ValueError('Got {0}, expected unicode or bytes'.format(
                         type(password)))
    if re.match(SCHEME_RE, password, re.IGNORECASE):
        # Just ensure we're getting bytes back.
        if isinstance(password, unicode):
            return password.encode('us-ascii')
        assert isinstance(password, bytes), 'Expected bytes'
        return password
    if scheme is None:
        password_scheme = lookup_scheme(config.passwords.password_scheme)
    elif scheme in Schemes:
        password_scheme = scheme
    else:
        password_scheme = lookup_scheme(scheme)
    if password_scheme is None:
        raise ValueError('Bad password scheme: {0}'.format(scheme))
    return make_secret(password, password_scheme)



# Password generation.

_vowels = tuple('aeiou')
_consonants = tuple(c for c in ascii_lowercase if c not in _vowels)
_syllables = tuple(x + y for (x, y) in
                   chain(product(_vowels, _consonants),
                         product(_consonants, _vowels)))


def make_user_friendly_password(length=None):
    """Make a random *user friendly* password.

    Such passwords are nominally easier to pronounce and thus remember.  Their
    security in relationship to purely random passwords has not been
    determined.

    :param length: Minimum length in characters for the resulting password.
        The password will always be an even number of characters.  When
        omitted, the system default length will be used.
    :type length: int
    :return: The user friendly password.
    :rtype: unicode
    """
    if length is None:
        length = int(config.passwords.password_length)
    syllables = []
    while len(syllables) * 2 < length:
        syllables.append(random.choice(_syllables))
    return EMPTYSTRING.join(syllables)[:length]
