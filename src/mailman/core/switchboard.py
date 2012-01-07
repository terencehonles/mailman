# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
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

"""Queuing and dequeuing message/metadata pickle files.

Messages are represented as email.message.Message objects (or an instance ofa
subclass).  Metadata is represented as a Python dictionary.  For every
message/metadata pair in a queue, a single file containing two pickles is
written.  First, the message is written to the pickle, then the metadata
dictionary is written.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Switchboard',
    ]


import os
import time
import email
import pickle
import cPickle
import hashlib
import logging

from zope.interface import implements

from mailman.config import config
from mailman.email.message import Message
from mailman.interfaces.switchboard import ISwitchboard
from mailman.utilities.filesystem import makedirs
from mailman.utilities.string import expand


# 20 bytes of all bits set, maximum hashlib.sha.digest() value.
shamax = 0xffffffffffffffffffffffffffffffffffffffffL
# Small increment to add to time in case two entries have the same time.  This
# prevents skipping one of two entries with the same time until the next pass.
DELTA = .0001
# We count the number of times a file has been moved to .bak and recovered.
# In order to prevent loops and a message flood, when the count reaches this
# value, we move the file to the bad queue as a .psv.
MAX_BAK_COUNT = 3

elog = logging.getLogger('mailman.error')



class Switchboard:
    implements(ISwitchboard)

    @staticmethod
    def initialize():
        """Initialize the global switchboards for input/output."""
        for conf in config.runner_configs:
            name = conf.name.split('.')[-1]
            assert name not in config.switchboards, (
                'Duplicate runner name: {0}'.format(name))
            substitutions = config.paths
            substitutions['name'] = name
            path = expand(conf.path, substitutions)
            config.switchboards[name] = Switchboard(name, path)

    def __init__(self, name, queue_directory,
                 slice=None, numslices=1, recover=False):
        """Create a switchboard object.

        :param name: The queue name.
        :type name: str
        :param queue_directory: The queue directory.
        :type queue_directory: str
        :param slice: The slice number for this switchboard, or None.  If not
            None, it must be [0..`numslices`).
        :type slice: int or None
        :param numslices: The total number of slices to split this queue
            directory into.  It must be a power of 2.
        :type numslices: int
        :param recover: True if backup files should be recovered.
        :type recover: bool
        """
        assert (numslices & (numslices - 1)) == 0, (
            'Not a power of 2: {0}'.format(numslices))
        self.name = name
        self.queue_directory = queue_directory
        # If configured to, create the directory if it doesn't yet exist.
        if config.create_paths:
            makedirs(self.queue_directory, 0770)
        # Fast track for no slices
        self._lower = None
        self._upper = None
        # BAW: test performance and end-cases of this algorithm
        if numslices <> 1:
            self._lower = ((shamax + 1) * slice) / numslices
            self._upper = (((shamax + 1) * (slice + 1)) / numslices) - 1
        if recover:
            self.recover_backup_files()

    def enqueue(self, _msg, _metadata=None, **_kws):
        """See `ISwitchboard`."""
        if _metadata is None:
            _metadata = {}
        # Calculate the SHA hexdigest of the message to get a unique base
        # filename.  We're also going to use the digest as a hash into the set
        # of parallel runner processes.
        data = _metadata.copy()
        data.update(_kws)
        listname = data.get('listname', '--nolist--')
        # Get some data for the input to the sha hash.
        now = time.time()
        if data.get('_plaintext'):
            protocol = 0
            msgsave = cPickle.dumps(str(_msg), protocol)
        else:
            protocol = pickle.HIGHEST_PROTOCOL
            msgsave = cPickle.dumps(_msg, protocol)
        # listname is unicode but the input to the hash function must be an
        # 8-bit string (eventually, a bytes object).
        hashfood = msgsave + listname.encode('utf-8') + repr(now)
        # Encode the current time into the file name for FIFO sorting.  The
        # file name consists of two parts separated by a '+': the received
        # time for this message (i.e. when it first showed up on this system)
        # and the sha hex digest.
        rcvtime = data.setdefault('received_time', now)
        filebase = repr(rcvtime) + '+' + hashlib.sha1(hashfood).hexdigest()
        filename = os.path.join(self.queue_directory, filebase + '.pck')
        tmpfile = filename + '.tmp'
        # Always add the metadata schema version number
        data['version'] = config.QFILE_SCHEMA_VERSION
        # Filter out volatile entries.  Use .keys() so that we can mutate the
        # dictionary during the iteration.
        for k in data.keys():
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
        """See `ISwitchboard`."""
        # Calculate the filename from the given filebase.
        filename = os.path.join(self.queue_directory, filebase + '.pck')
        backfile = os.path.join(self.queue_directory, filebase + '.bak')
        # Read the message object and metadata.
        with open(filename) as fp:
            # Move the file to the backup file name for processing.  If this
            # process crashes uncleanly the .bak file will be used to
            # re-instate the .pck file in order to try again.
            os.rename(filename, backfile)
            msg = cPickle.load(fp)
            data = cPickle.load(fp)
        if data.get('_parsemsg'):
            # Calculate the original size of the text now so that we won't
            # have to generate the message later when we do size restriction
            # checking.
            original_size = len(msg)
            msg = email.message_from_string(msg, Message)
            msg.original_size = original_size
            data['original_size'] = original_size
        return msg, data

    def finish(self, filebase, preserve=False):
        """See `ISwitchboard`."""
        bakfile = os.path.join(self.queue_directory, filebase + '.bak')
        try:
            if preserve:
                bad_dir = config.switchboards['bad'].queue_directory
                psvfile = os.path.join(bad_dir, filebase + '.psv')
                os.rename(bakfile, psvfile)
            else:
                os.unlink(bakfile)
        except EnvironmentError:
            elog.exception(
                'Failed to unlink/preserve backup file: %s', bakfile)

    @property
    def files(self):
        """See `ISwitchboard`."""
        return self.get_files()

    def get_files(self, extension='.pck'):
        """See `ISwitchboard`."""
        times = {}
        lower = self._lower
        upper = self._upper
        for f in os.listdir(self.queue_directory):
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
        return [times[key] for key in sorted(times)]

    def recover_backup_files(self):
        """See `ISwitchboard`."""
        # Move all .bak files in our slice to .pck.  It's impossible for both
        # to exist at the same time, so the move is enough to ensure that our
        # normal dequeuing process will handle them.  We keep count in
        # _bak_count in the metadata of the number of times we recover this
        # file.  When the count reaches MAX_BAK_COUNT, we move the .bak file
        # to a .psv file in the bad queue.
        for filebase in self.get_files('.bak'):
            src = os.path.join(self.queue_directory, filebase + '.bak')
            dst = os.path.join(self.queue_directory, filebase + '.pck')
            with open(src, 'rb+') as fp:
                try:
                    msg = cPickle.load(fp)
                    data_pos = fp.tell()
                    data = cPickle.load(fp)
                except Exception as error:
                    # If unpickling throws any exception, just log and
                    # preserve this entry
                    elog.error('Unpickling .bak exception: %s\n'
                               'Preserving file: %s', error, filebase)
                    self.finish(filebase, preserve=True)
                else:
                    data['_bak_count'] = data.get('_bak_count', 0) + 1
                    fp.seek(data_pos)
                    if data.get('_parsemsg'):
                        protocol = 0
                    else:
                        protocol = 1
                    cPickle.dump(data, fp, protocol)
                    fp.truncate()
                    fp.flush()
                    os.fsync(fp.fileno())
                    if data['_bak_count'] >= MAX_BAK_COUNT:
                        elog.error('.bak file max count, preserving file: %s',
                                   filebase)
                        self.finish(filebase, preserve=True)
                    else:
                        os.rename(src, dst)
