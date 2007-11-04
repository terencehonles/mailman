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

"""Implementations of the IPendable and IPending interfaces."""

import time
import random
import hashlib
import datetime

from storm.locals import *
from zope.interface import implements
from zope.interface.verify import verifyObject

from Mailman.configuration import config
from Mailman.database import Model
from Mailman.interfaces import (
    IPendings, IPendable, IPendedKeyValue, IPended)



class PendedKeyValue(Model):
    """A pended key/value pair, tied to a token."""

    implements(IPendedKeyValue)

    id = Int(primary=True)
    key = Unicode()
    value = Unicode()


class Pended(Model):
    """A pended event, tied to a token."""

    implements(IPended)

    id = Int(primary=True)
    token = Unicode()
    expiration_date = DateTime()
    key_values = Reference(id, PendedKeyValue.id)



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
            if Pended.query.filter_by(token=token).count() == 0:
                break
        else:
            raise AssertionError('Could not find a valid pendings token')
        # Create the record, and then the individual key/value pairs.
        pending = Pended(
            token=token,
            expiration_date=datetime.datetime.now() + lifetime)
        for key, value in pendable.items():
            PendedKeyValue(key=key, value=value, pended=pending)
        return token

    def confirm(self, token, expunge=True):
        pendings = Pended.query.filter_by(token=token)
        if pendings.count() == 0:
            return None
        assert pendings.count() == 1, (
            'Unexpected token count: %d' % pendings.count())
        pending = pendings[0]
        pendable = UnpendedPendable()
        # Find all PendedKeyValue entries that are associated with the pending
        # object's ID.
        q = PendedKeyValue.query.filter(
            PendedKeyValue.c.pended_id == Pended.c.id).filter(
            Pended.c.id == pending.id)
        for keyvalue in q.all():
            pendable[keyvalue.key] = keyvalue.value
            if expunge:
                keyvalue.delete()
        if expunge:
            pending.delete()
        return pendable

    def evict(self):
        now = datetime.datetime.now()
        for pending in Pended.query.filter_by().all():
            if pending.expiration_date < now:
                # Find all PendedKeyValue entries that are associated with the
                # pending object's ID.
                q = PendedKeyValue.query.filter(
                    PendedKeyValue.c.pended_id == Pended.c.id).filter(
                    Pended.c.id == pending.id)
                for keyvalue in q:
                    keyvalue.delete()
                pending.delete()
