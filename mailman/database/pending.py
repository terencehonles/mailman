# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Implementations of the IPendable and IPending interfaces."""

import sys
import time
import random
import hashlib
import datetime

from storm.locals import *
from zope.interface import implements
from zope.interface.verify import verifyObject

from mailman.configuration import config
from mailman.database.model import Model
from mailman.interfaces import (
    IPendable, IPended, IPendedKeyValue, IPendings)



class PendedKeyValue(Model):
    """A pended key/value pair, tied to a token."""

    implements(IPendedKeyValue)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    id = Int(primary=True)
    key = Unicode()
    value = Unicode()
    pended_id = Int()


class Pended(Model):
    """A pended event, tied to a token."""

    implements(IPended)

    def __init__(self, token, expiration_date):
        self.token = token
        self.expiration_date = expiration_date

    id = Int(primary=True)
    token = RawStr()
    expiration_date = DateTime()
    key_values = ReferenceSet(id, PendedKeyValue.pended_id)



class UnpendedPendable(dict):
    implements(IPendable)



class Pendings(object):
    """Implementation of the IPending interface."""

    implements(IPendings)

    def add(self, pendable, lifetime=None):
        verifyObject(IPendable, pendable)
        # Calculate the token and the lifetime.
        if lifetime is None:
            lifetime = config.PENDING_REQUEST_LIFE
        # Calculate a unique token.  Algorithm vetted by the Timbot.  time()
        # has high resolution on Linux, clock() on Windows.  random gives us
        # about 45 bits in Python 2.2, 53 bits on Python 2.3.  The time and
        # clock values basically help obscure the random number generator, as
        # does the hash calculation.  The integral parts of the time values
        # are discarded because they're the most predictable bits.
        for attempts in range(3):
            now = time.time()
            x = random.random() + now % 1.0 + time.clock() % 1.0
            # Use sha1 because it produces shorter strings.
            token = hashlib.sha1(repr(x)).hexdigest()
            # In practice, we'll never get a duplicate, but we'll be anal
            # about checking anyway.
            if config.db.store.find(Pended, token=token).count() == 0:
                break
        else:
            raise AssertionError('Could not find a valid pendings token')
        # Create the record, and then the individual key/value pairs.
        pending = Pended(
            token=token,
            expiration_date=datetime.datetime.now() + lifetime)
        for key, value in pendable.items():
            if isinstance(key, str):
                key = unicode(key, 'utf-8')
            if isinstance(value, str):
                value = unicode(value, 'utf-8')
            elif type(value) is int:
                value = u'__builtin__.int\1%s' % value
            elif type(value) is float:
                value = u'__builtin__.float\1%s' % value
            elif type(value) is bool:
                value = u'__builtin__.bool\1%s' % value
            elif type(value) is list:
                # We expect this to be a list of strings.
                value = u'mailman.database.pending.unpack_list\1%s' % (
                    '\2'.join(value))
            keyval = PendedKeyValue(key=key, value=value)
            pending.key_values.add(keyval)
        config.db.store.add(pending)
        return token

    def confirm(self, token, expunge=True):
        store = config.db.store
        pendings = store.find(Pended, token=token)
        if pendings.count() == 0:
            return None
        assert pendings.count() == 1, (
            'Unexpected token count: %d' % pendings.count())
        pending = pendings[0]
        pendable = UnpendedPendable()
        # Find all PendedKeyValue entries that are associated with the pending
        # object's ID.  Watch out for type conversions.
        for keyvalue in store.find(PendedKeyValue,
                                   PendedKeyValue.pended_id == pending.id):
            if keyvalue.value is not None and '\1' in keyvalue.value:
                typename, value = keyvalue.value.split('\1', 1)
                package, classname = typename.rsplit('.', 1)
                __import__(package)
                module = sys.modules[package]
                pendable[keyvalue.key] = getattr(module, classname)(value)
            else:
                pendable[keyvalue.key] = keyvalue.value
            if expunge:
                store.remove(keyvalue)
        if expunge:
            store.remove(pending)
        return pendable

    def evict(self):
        store = config.db.store
        now = datetime.datetime.now()
        for pending in store.find(Pended):
            if pending.expiration_date < now:
                # Find all PendedKeyValue entries that are associated with the
                # pending object's ID.
                q = store.find(PendedKeyValue,
                               PendedKeyValue.pended_id == pending.id)
                for keyvalue in q:
                    store.remove(keyvalue)
                store.remove(pending)



def unpack_list(value):
    return value.split('\2')
