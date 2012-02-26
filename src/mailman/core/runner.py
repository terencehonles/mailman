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

"""The process runner base class."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Runner',
    ]


import time
import logging
import traceback

from cStringIO import StringIO
from lazr.config import as_boolean, as_timedelta
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.core.switchboard import Switchboard
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.runner import IRunner
from mailman.utilities.string import expand


dlog = logging.getLogger('mailman.debug')
elog = logging.getLogger('mailman.error')



class Runner:
    implements(IRunner)

    intercept_signals = True

    def __init__(self, name, slice=None):
        """Create a runner.

        :param slice: The slice number for this runner.  This is passed
            directly to the underlying `ISwitchboard` object.  This is ignored
            for runners that don't manage a queue.
        :type slice: int or None
        """
        # Grab the configuration section.
        self.name = name
        section = getattr(config, 'runner.' + name)
        substitutions = config.paths
        substitutions['name'] = name
        self.queue_directory = expand(section.path, substitutions)
        numslices = int(section.instances)
        self.switchboard = Switchboard(
            name, self.queue_directory, slice, numslices, True)
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
        # Start the main loop for this runner.
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
                msgdata['whichq'] = self.switchboard.name
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
            dlog.debug('[%s] committing transaction', me)
            config.db.commit()
            dlog.debug('[%s] checking short circuit', me)
            if self._short_circuit():
                dlog.debug('[%s] short circuiting', me)
                break
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
        missing = object()
        listname = msgdata.get('listname', missing)
        mlist = (None
                 if listname is missing
                 else getUtility(IListManager).get(unicode(listname)))
        if mlist is None:
            elog.error(
                '%s runner "%s" shunting message for missing list: %s',
                msg['message-id'], self.name,
                ('n/a' if listname is missing else listname))
            config.switchboards['shunt'].enqueue(msg, msgdata)
            return
        # Now process this message.  We also want to set up the language
        # context for this message.  The context will be the preferred
        # language for the user if the sender is a member of the list, or it
        # will be the list's preferred language.  However, we must take
        # special care to reset the defaults, otherwise subsequent messages
        # may be translated incorrectly.
        if mlist is None:
            language_manager = getUtility(ILanguageManager)
            language = language_manager[config.mailman.default_language]
        elif msg.sender:
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
        pass

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
