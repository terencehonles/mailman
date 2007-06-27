# Copyright (C) 2001-2007 by the Free Software Foundation, Inc.
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

"""Queing and dequeuing message/metadata pickle files.

Messages are represented as email.message.Message objects (or an instance ofa
subclass).  Metadata is represented as a Python dictionary.  For every
message/metadata pair in a queue, a single file containing two pickles is
written.  First, the message is written to the pickle, then the metadata
dictionary is written.
"""

from __future__ import with_statement

import os
import sha
import time
import email
import errno
import cPickle
import logging
import marshal

from zope.interface import implements

from Mailman import Message
from Mailman import Utils
from Mailman.configuration import config
from Mailman.interfaces import ISwitchboard

# 20 bytes of all bits set, maximum sha.digest() value
shamax = 0xffffffffffffffffffffffffffffffffffffffffL

# Small increment to add to time in case two entries have the same time.  This
# prevents skipping one of two entries with the same time until the next pass.
DELTA = .0001

elog = logging.getLogger('mailman.error')



class Switchboard:
    implements(ISwitchboard)

    def __init__(self, whichq, slice=None, numslices=1, recover=False):
        self._whichq = whichq
        # Create the directory if it doesn't yet exist.
        Utils.makedirs(self._whichq, 0770)
        # Fast track for no slices
        self._lower = None
        self._upper = None
        # BAW: test performance and end-cases of this algorithm
        if numslices <> 1:
            self._lower = ((shamax + 1) * slice) / numslices
            self._upper = (((shamax + 1) * (slice + 1)) / numslices) - 1
        if recover:
            self.recover_backup_files()

    @property
    def queue_directory(self):
        return self._whichq

    def enqueue(self, _msg, _metadata=None, **_kws):
        if _metadata is None:
            _metadata = {}
        # Calculate the SHA hexdigest of the message to get a unique base
        # filename.  We're also going to use the digest as a hash into the set
        # of parallel qrunner processes.
        data = _metadata.copy()
        data.update(_kws)
        listname = data.get('listname', '--nolist--')
        # Get some data for the input to the sha hash.
        now = time.time()
        if not data.get('_plaintext'):
            protocol = 1
            msgsave = cPickle.dumps(_msg, protocol)
        else:
            protocol = 0
            msgsave = cPickle.dumps(str(_msg), protocol)
        # listname is unicode but the input to the hash function must be an
        # 8-bit string (eventually, a bytes object).
        hashfood = msgsave + listname.encode('utf-8') + repr(now)
        # Encode the current time into the file name for FIFO sorting.  The
        # file name consists of two parts separated by a '+': the received
        # time for this message (i.e. when it first showed up on this system)
        # and the sha hex digest.
        rcvtime = data.setdefault('received_time', now)
        filebase = repr(rcvtime) + '+' + sha.new(hashfood).hexdigest()
        filename = os.path.join(self._whichq, filebase + '.pck')
        tmpfile = filename + '.tmp'
        # Always add the metadata schema version number
        data['version'] = config.QFILE_SCHEMA_VERSION
        # Filter out volatile entries
        for k in data:
            if k.startswith('_'):
                del data[k]
        # We have to tell the dequeue() method whether to parse the message
        # object or not.
        data['_parsemsg'] = (protocol == 0)
        # Write to the pickle file the message object and metadata.
        with open(tmpfile, 'w') as fp:
            fp.write(msgsave)
            cPickle.dump(data, fp, protocol)
            fp.flush()
            os.fsync(fp.fileno())
        os.rename(tmpfile, filename)
        return filebase

    def dequeue(self, filebase):
        # Calculate the filename from the given filebase.
        filename = os.path.join(self._whichq, filebase + '.pck')
        backfile = os.path.join(self._whichq, filebase + '.bak')
        # Read the message object and metadata.
        with open(filename) as fp:
            # Move the file to the backup file name for processing.  If this
            # process crashes uncleanly the .bak file will be used to
            # re-instate the .pck file in order to try again.  XXX what if
            # something caused Python to constantly crash?  Is it possible
            # that we'd end up mail bombing recipients or crushing the
            # archiver?  How would we defend against that?
            os.rename(filename, backfile)
            msg = cPickle.load(fp)
            data = cPickle.load(fp)
        if data.get('_parsemsg'):
            msg = email.message_from_string(msg, Message.Message)
        return msg, data

    def finish(self, filebase, preserve=False):
        bakfile = os.path.join(self._whichq, filebase + '.bak')
        try:
            if preserve:
                psvfile = os.path.join(config.SHUNTQUEUE_DIR,
                                       filebase + '.psv')
                # Create the directory if it doesn't yet exist.
                Utils.makedirs(config.SHUNTQUEUE_DIR, 0770)
                os.rename(bakfile, psvfile)
            else:
                os.unlink(bakfile)
        except EnvironmentError, e:
            elog.exception('Failed to unlink/preserve backup file: %s',
                           bakfile)

    @property
    def files(self):
        return self.get_files()

    def get_files(self, extension='.pck'):
        times = {}
        lower = self._lower
        upper = self._upper
        for f in os.listdir(self._whichq):
            # By ignoring anything that doesn't end in .pck, we ignore
            # tempfiles and avoid a race condition.
            filebase, ext = os.path.splitext(f)
            if ext <> extension:
                continue
            when, digest = filebase.split('+', 1)
            # Throw out any files which don't match our bitrange.  BAW: test
            # performance and end-cases of this algorithm.  MAS: both
            # comparisons need to be <= to get complete range.
            if lower is None or (lower <= long(digest, 16) <= upper):
                key = float(when)
                while key in times:
                    key += DELTA
                times[key] = filebase
        # FIFO sort
        for key in sorted(times):
            yield times[key]

    def recover_backup_files(self):
        # Move all .bak files in our slice to .pck.  It's impossible for both
        # to exist at the same time, so the move is enough to ensure that our
        # normal dequeuing process will handle them.
        for filebase in self.get_files('.bak'):
            src = os.path.join(self._whichq, filebase + '.bak')
            dst = os.path.join(self._whichq, filebase + '.pck')
            os.rename(src, dst)
