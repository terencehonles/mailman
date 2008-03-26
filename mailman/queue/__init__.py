# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

__metaclass__ = type
__all__ = [
    'Runner',
    'Switchboard',
    ]


import os
import sha
import time
import email
import errno
import cPickle
import logging
import marshal
import traceback

from cStringIO import StringIO
from zope.interface import implements

from mailman import i18n
from mailman import Message
from mailman import Utils
from mailman.configuration import config
from mailman.interfaces import IRunner, ISwitchboard

# 20 bytes of all bits set, maximum sha.digest() value
shamax = 0xffffffffffffffffffffffffffffffffffffffffL

# Small increment to add to time in case two entries have the same time.  This
# prevents skipping one of two entries with the same time until the next pass.
DELTA = .0001

log = logging.getLogger('mailman.error')



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
            # Calculate the original size of the text now so that we won't
            # have to generate the message later when we do size restriction
            # checking.
            original_size = len(msg)
            msg = email.message_from_string(msg, Message.Message)
            msg.original_size = original_size
            data['original_size'] = original_size
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
            log.exception('Failed to unlink/preserve backup file: %s', bakfile)

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
        return [times[key] for key in sorted(times)]

    def recover_backup_files(self):
        # Move all .bak files in our slice to .pck.  It's impossible for both
        # to exist at the same time, so the move is enough to ensure that our
        # normal dequeuing process will handle them.
        for filebase in self.get_files('.bak'):
            src = os.path.join(self._whichq, filebase + '.bak')
            dst = os.path.join(self._whichq, filebase + '.pck')
            os.rename(src, dst)



class Runner:
    implements(IRunner)

    QDIR = None
    SLEEPTIME = None

    def __init__(self, slice=None, numslices=1):
        self._kids = {}
        # Create our own switchboard.  Don't use the switchboard cache because
        # we want to provide slice and numslice arguments.
        self._switchboard = Switchboard(self.QDIR, slice, numslices, True)
        # Create the shunt switchboard
        self._shunt = Switchboard(config.SHUNTQUEUE_DIR)
        self._stop = False
        if self.SLEEPTIME is None:
            self.SLEEPTIME = config.QRUNNER_SLEEP_TIME

    def __repr__(self):
        return '<%s at %s>' % (self.__class__.__name__, id(self))

    def stop(self):
        self._stop = True

    def run(self):
        # Start the main loop for this queue runner.
        try:
            try:
                while True:
                    # Once through the loop that processes all the files in
                    # the queue directory.
                    filecnt = self._oneloop()
                    # Do the periodic work for the subclass.  BAW: this
                    # shouldn't be called here.  There should be one more
                    # _doperiodic() call at the end of the _oneloop() loop.
                    self._doperiodic()
                    # If the stop flag is set, we're done.
                    if self._stop:
                        break
                    # Give the runner an opportunity to snooze for a while,
                    # but pass it the file count so it can decide whether to
                    # do more work now or not.
                    self._snooze(filecnt)
            except KeyboardInterrupt:
                pass
        finally:
            # We've broken out of our main loop, so we want to reap all the
            # subprocesses we've created and do any other necessary cleanups.
            self._cleanup()

    def _oneloop(self):
        # First, list all the files in our queue directory.
        # Switchboard.files() is guaranteed to hand us the files in FIFO
        # order.  Return an integer count of the number of files that were
        # available for this qrunner to process.
        files = self._switchboard.files
        for filebase in files:
            try:
                # Ask the switchboard for the message and metadata objects
                # associated with this filebase.
                msg, msgdata = self._switchboard.dequeue(filebase)
            except Exception, e:
                # This used to just catch email.Errors.MessageParseError,
                # but other problems can occur in message parsing, e.g.
                # ValueError, and exceptions can occur in unpickling too.
                # We don't want the runner to die, so we just log and skip
                # this entry, but preserve it for analysis.
                self._log(e)
                log.error('Skipping and preserving unparseable message: %s',
                          filebase)
                self._switchboard.finish(filebase, preserve=True)
                config.db.abort()
                continue
            try:
                self._onefile(msg, msgdata)
                self._switchboard.finish(filebase)
            except Exception, e:
                # All runners that implement _dispose() must guarantee that
                # exceptions are caught and dealt with properly.  Still, there
                # may be a bug in the infrastructure, and we do not want those
                # to cause messages to be lost.  Any uncaught exceptions will
                # cause the message to be stored in the shunt queue for human
                # intervention.
                self._log(e)
                # Put a marker in the metadata for unshunting
                msgdata['whichq'] = self._switchboard.queue_directory
                # It is possible that shunting can throw an exception, e.g. a
                # permissions problem or a MemoryError due to a really large
                # message.  Try to be graceful.
                try:
                    new_filebase = self._shunt.enqueue(msg, msgdata)
                    log.error('SHUNTING: %s', new_filebase)
                    self._switchboard.finish(filebase)
                except Exception, e:
                    # The message wasn't successfully shunted.  Log the
                    # exception and try to preserve the original queue entry
                    # for possible analysis.
                    self._log(e)
                    log.error('SHUNTING FAILED, preserving original entry: %s',
                              filebase)
                    self._switchboard.finish(filebase, preserve=True)
                    config.db.abort()
            # Other work we want to do each time through the loop.
            Utils.reap(self._kids, once=True)
            self._doperiodic()
            if self._shortcircuit():
                break
            config.db.commit()
        return len(files)

    def _onefile(self, msg, msgdata):
        # Do some common sanity checking on the message metadata.  It's got to
        # be destined for a particular mailing list.  This switchboard is used
        # to shunt off badly formatted messages.  We don't want to just trash
        # them because they may be fixable with human intervention.  Just get
        # them out of our site though.
        #
        # Find out which mailing list this message is destined for.
        listname = msgdata.get('listname')
        mlist = config.db.list_manager.get(listname)
        if not mlist:
            log.error('Dequeuing message destined for missing list: %s',
                      listname)
            self._shunt.enqueue(msg, msgdata)
            return
        # Now process this message, keeping track of any subprocesses that may
        # have been spawned.  We'll reap those later.
        #
        # We also want to set up the language context for this message.  The
        # context will be the preferred language for the user if a member of
        # the list, or the list's preferred language.  However, we must take
        # special care to reset the defaults, otherwise subsequent messages
        # may be translated incorrectly.  BAW: I'm not sure I like this
        # approach, but I can't think of anything better right now.
        sender = msg.get_sender()
        member = mlist.members.get_member(sender)
        if member:
            lang = member.preferred_language
        else:
            lang = mlist.preferred_language
        with i18n.using_language(lang):
            msgdata['lang'] = lang
            keepqueued = self._dispose(mlist, msg, msgdata)
        # Keep tabs on any child processes that got spawned.
        kids = msgdata.get('_kids')
        if kids:
            self._kids.update(kids)
        if keepqueued:
            self._switchboard.enqueue(msg, msgdata)

    def _log(self, exc):
        log.error('Uncaught runner exception: %s', exc)
        s = StringIO()
        traceback.print_exc(file=s)
        log.error('%s', s.getvalue())

    #
    # Subclasses can override these methods.
    #
    def _cleanup(self):
        """Clean up upon exit from the main processing loop.

        Called when the Runner's main loop is stopped, this should perform
        any necessary resource deallocation.  Its return value is irrelevant.
        """
        Utils.reap(self._kids)

    def _dispose(self, mlist, msg, msgdata):
        """Dispose of a single message destined for a mailing list.

        Called for each message that the Runner is responsible for, this is
        the primary overridable method for processing each message.
        Subclasses, must provide implementation for this method.

        mlist is the IMailingList instance this message is destined for.

        msg is the Message object representing the message.

        msgdata is a dictionary of message metadata.
        """
        raise NotImplementedError

    def _doperiodic(self):
        """Do some processing `every once in a while'.

        Called every once in a while both from the Runner's main loop, and
        from the Runner's hash slice processing loop.  You can do whatever
        special periodic processing you want here, and the return value is
        irrelevant.
        """
        pass

    def _snooze(self, filecnt):
        """Sleep for a little while.

        filecnt is the number of messages in the queue the last time through.
        Sub-runners can decide to continue to do work, or sleep for a while
        based on this value.  By default, we only snooze if there was nothing
        to do last time around.
        """
        if filecnt or float(self.SLEEPTIME) <= 0:
            return
        time.sleep(float(self.SLEEPTIME))

    def _shortcircuit(self):
        """Return a true value if the individual file processing loop should
        exit before it's finished processing each message in the current slice
        of hash space.  A false value tells _oneloop() to continue processing
        until the current snapshot of hash space is exhausted.

        You could, for example, implement a throttling algorithm here.
        """
        return self._stop
