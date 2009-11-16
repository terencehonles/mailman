# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""Queing and dequeuing message/metadata pickle files.

Messages are represented as email.message.Message objects (or an instance ofa
subclass).  Metadata is represented as a Python dictionary.  For every
message/metadata pair in a queue, a single file containing two pickles is
written.  First, the message is written to the pickle, then the metadata
dictionary is written.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Runner',
    'Switchboard',
    ]


import os
import sys
import time
import email
import errno
import pickle
import cPickle
import hashlib
import logging
import marshal
import traceback

from cStringIO import StringIO
from lazr.config import as_boolean, as_timedelta
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.email.message import Message
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.runner import IRunner
from mailman.interfaces.switchboard import ISwitchboard
from mailman.utilities.filesystem import makedirs
from mailman.utilities.string import expand


# 20 bytes of all bits set, maximum hashlib.sha.digest() value
shamax = 0xffffffffffffffffffffffffffffffffffffffffL

# Small increment to add to time in case two entries have the same time.  This
# prevents skipping one of two entries with the same time until the next pass.
DELTA = .0001
DOT = '.'
# We count the number of times a file has been moved to .bak and recovered.
# In order to prevent loops and a message flood, when the count reaches this
# value, we move the file to the bad queue as a .psv.
MAX_BAK_COUNT = 3

elog = logging.getLogger('mailman.error')
dlog = logging.getLogger('mailman.debug')



class Switchboard:
    implements(ISwitchboard)

    @staticmethod
    def initialize():
        """Initialize the global switchboards for input/output."""
        for conf in config.qrunner_configs:
            name = conf.name.split('.')[-1]
            assert name not in config.switchboards, (
                'Duplicate qrunner name: {0}'.format(name))
            substitutions = config.paths
            substitutions['name'] = name
            path = expand(conf.path, substitutions)
            config.switchboards[name] = Switchboard(path)

    def __init__(self, queue_directory,
                 slice=None, numslices=1, recover=False):
        """Create a switchboard object.

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
        self.queue_directory = queue_directory
        # Create the directory if it doesn't yet exist.
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
        # of parallel qrunner processes.
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
            fp = open(src, 'rb+')
            try:
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
            finally:
                fp.close()



class Runner:
    implements(IRunner)

    intercept_signals = True

    def __init__(self, name, slice=None):
        """Create a queue runner.

        :param slice: The slice number for this queue runner.  This is passed
            directly to the underlying `ISwitchboard` object.
        :type slice: int or None
        """
        # Grab the configuration section.
        self.name = name
        section = getattr(config, 'qrunner.' + name)
        substitutions = config.paths
        substitutions['name'] = name
        self.queue_directory = expand(section.path, substitutions)
        numslices = int(section.instances)
        self.switchboard = Switchboard(
            self.queue_directory, slice, numslices, True)
        self.sleep_time = as_timedelta(section.sleep_time)
        # sleep_time is a timedelta; turn it into a float for time.sleep().
        self.sleep_float = (86400 * self.sleep_time.days +
                            self.sleep_time.seconds +
                            self.sleep_time.microseconds / 1.0e6)
        self.max_restarts = int(section.max_restarts)
        self.start = as_boolean(section.start)
        self._stop = False

    def __repr__(self):
        return '<{0} at {1:#x}>'.format(self.__class__.__name__, id(self))

    def stop(self):
        """See `IRunner`."""
        self._stop = True

    def run(self):
        """See `IRunner`."""
        # Start the main loop for this queue runner.
        try:
            while True:
                # Once through the loop that processes all the files in the
                # queue directory.
                filecnt = self._one_iteration()
                # Do the periodic work for the subclass.
                self._do_periodic()
                # If the stop flag is set, we're done.
                if self._stop:
                    break
                # Give the runner an opportunity to snooze for a while, but
                # pass it the file count so it can decide whether to do more
                # work now or not.
                self._snooze(filecnt)
        except KeyboardInterrupt:
            pass
        finally:
            self._clean_up()

    def _one_iteration(self):
        """See `IRunner`."""
        me = self.__class__.__name__
        dlog.debug('[%s] starting oneloop', me)
        # List all the files in our queue directory.  The switchboard is
        # guaranteed to hand us the files in FIFO order.
        files = self.switchboard.files
        for filebase in files:
            dlog.debug('[%s] processing filebase: %s', me, filebase)
            try:
                # Ask the switchboard for the message and metadata objects
                # associated with this queue file.
                msg, msgdata = self.switchboard.dequeue(filebase)
            except Exception as error:
                # This used to just catch email.Errors.MessageParseError, but
                # other problems can occur in message parsing, e.g.
                # ValueError, and exceptions can occur in unpickling too.  We
                # don't want the runner to die, so we just log and skip this
                # entry, but preserve it for analysis.
                self._log(error)
                elog.error('Skipping and preserving unparseable message: %s',
                           filebase)
                self.switchboard.finish(filebase, preserve=True)
                config.db.abort()
                continue
            try:
                dlog.debug('[%s] processing onefile', me)
                self._process_one_file(msg, msgdata)
                dlog.debug('[%s] finishing filebase: %s', me, filebase)
                self.switchboard.finish(filebase)
            except Exception as error:
                # All runners that implement _dispose() must guarantee that
                # exceptions are caught and dealt with properly.  Still, there
                # may be a bug in the infrastructure, and we do not want those
                # to cause messages to be lost.  Any uncaught exceptions will
                # cause the message to be stored in the shunt queue for human
                # intervention.
                self._log(error)
                # Put a marker in the metadata for unshunting.
                msgdata['whichq'] = self.switchboard.queue_directory
                # It is possible that shunting can throw an exception, e.g. a
                # permissions problem or a MemoryError due to a really large
                # message.  Try to be graceful.
                try:
                    shunt = config.switchboards['shunt']
                    new_filebase = shunt.enqueue(msg, msgdata)
                    elog.error('SHUNTING: %s', new_filebase)
                    self.switchboard.finish(filebase)
                except Exception as error:
                    # The message wasn't successfully shunted.  Log the
                    # exception and try to preserve the original queue entry
                    # for possible analysis.
                    self._log(error)
                    elog.error(
                        'SHUNTING FAILED, preserving original entry: %s',
                        filebase)
                    self.switchboard.finish(filebase, preserve=True)
                config.db.abort()
            # Other work we want to do each time through the loop.
            dlog.debug('[%s] doing periodic', me)
            self._do_periodic()
            dlog.debug('[%s] checking short circuit', me)
            if self._short_circuit():
                dlog.debug('[%s] short circuiting', me)
                break
            dlog.debug('[%s] commiting', me)
            config.db.commit()
        dlog.debug('[%s] ending oneloop: %s', me, len(files))
        return len(files)

    def _process_one_file(self, msg, msgdata):
        """See `IRunner`."""
        # Do some common sanity checking on the message metadata.  It's got to
        # be destined for a particular mailing list.  This switchboard is used
        # to shunt off badly formatted messages.  We don't want to just trash
        # them because they may be fixable with human intervention.  Just get
        # them out of our sight.
        #
        # Find out which mailing list this message is destined for.
        listname = unicode(msgdata.get('listname'))
        mlist = getUtility(IListManager).get(listname)
        if mlist is None:
            elog.error('Dequeuing message destined for missing list: %s',
                       listname)
            config.switchboards['shunt'].enqueue(msg, msgdata)
            return
        # Now process this message.  We also want to set up the language
        # context for this message.  The context will be the preferred
        # language for the user if the sender is a member of the list, or it
        # will be the list's preferred language.  However, we must take
        # special care to reset the defaults, otherwise subsequent messages
        # may be translated incorrectly.
        if msg.sender:
            member = mlist.members.get_member(msg.sender)
            language = (member.preferred_language
                        if member is not None
                        else mlist.preferred_language)
        else:
            language = mlist.preferred_language
        with _.using(language.code):
            msgdata['lang'] = language.code
            keepqueued = self._dispose(mlist, msg, msgdata)
        if keepqueued:
            self.switchboard.enqueue(msg, msgdata)

    def _log(self, exc):
        elog.error('Uncaught runner exception: %s', exc)
        s = StringIO()
        traceback.print_exc(file=s)
        elog.error('%s', s.getvalue())

    def _clean_up(self):
        """See `IRunner`."""

    def _dispose(self, mlist, msg, msgdata):
        """See `IRunner`."""
        raise NotImplementedError

    def _do_periodic(self):
        """See `IRunner`."""
        pass

    def _snooze(self, filecnt):
        """See `IRunner`."""
        if filecnt or self.sleep_float <= 0:
            return
        time.sleep(self.sleep_float)

    def _short_circuit(self):
        """See `IRunner`."""
        return self._stop
