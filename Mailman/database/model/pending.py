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

from elixir import *
from zope.interface import implements
from zope.interface.verify import verifyObject

from Mailman.configuration import config
from Mailman.interfaces import IPending, IPendable

PEND_KIND = 'Mailman.database.model.pending.Pending'



class PendedKeyValue(Entity):
    """A pended key/value pair, tied to a token."""

    has_field('key',        Unicode)
    has_field('value',      Unicode)
    # Relationships
    belongs_to('pended',    of_kind=PEND_KIND)
    # Options
    using_options(shortnames=True)


class Pending(Entity):
    """A pended event, tied to a token."""

    has_field('token',              Unicode)
    has_field('expiration_date',    DateTime)
    # Options
    using_options(shortnames=True)



class UnpendedPendable(dict):
    implements(IPendable)



class Pendings(object):
    """Implementation of the IPending interface."""

    implements(IPending)

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
        while True:
            now = time.time()
            x = random.random() + now % 1.0 + time.clock() % 1.0
            # Use sha1 because it produces shorter strings.
            token = hashlib.sha1(repr(x)).hexdigest()
            # In practice, we'll never get a duplicate, but we'll be anal
            # about checking anyway.
            if not Pending.select_by(token=token):
                break
        # Create the record, and then the individual key/value pairs.
        pending = Pending(
            token=token,
            expiration_date=datetime.datetime.now() + lifetime)
        for key, value in pendable.items():
            PendedKeyValue(key=key, value=value, pended=pending)
        return token

    def confirm(self, token, expunge=True):
        pendings = Pending.select_by(token=token)
        assert 0 <= len(pendings) <= 1, 'Unexpected token search results'
        if len(pendings) == 0:
            return None
        pending = pendings[0]
        pendable = UnpendedPendable()
        # Find all PendedKeyValue entries that are associated with the pending
        # object's ID.
        q = PendedKeyValue.filter(
            PendedKeyValue.c.pended_id == Pending.c.id).filter(
            Pending.c.id == pending.id)
        for keyvalue in q.all():
            pendable[keyvalue.key] = keyvalue.value
            if expunge:
                keyvalue.delete()
        if expunge:
            pending.delete()
        return pendable

    def evict(self):
        now = datetime.datetime.now()
        for pending in Pending.select():
            if pending.expiration_date < now:
                # Find all PendedKeyValue entries that are associated with the
                # pending object's ID.
                q = PendedKeyValue.filter(
                    PendedKeyValue.c.pended_id == Pending.c.id).filter(
                    Pending.c.id == pending.id)
                for keyvalue in q:
                    keyvalue.delete()
                pending.delete()
