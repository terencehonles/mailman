# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""Various test helpers."""

from __future__ import with_statement

__metaclass__ = type
__all__ = [
    'TestableMaster',
    'digest_mbox',
    'get_queue_messages',
    'make_testable_runner',
    ]


import os
import time
import errno
import mailbox
import smtplib
import tempfile
import threading

from Queue import Empty, Queue
from datetime import datetime, timedelta

from mailman.bin.master import Loop as Master
from mailman.configuration import config
from mailman.queue import Switchboard
from mailman.tests.smtplistener import Server



def make_testable_runner(runner_class):
    """Create a queue runner that runs until its queue is empty.

    :param runner_class: An IRunner
    :return: A runner instance.
    """

    class EmptyingRunner(runner_class):
        """Stop processing when the queue is empty."""

        def _doperiodic(self):
            """Stop when the queue is empty."""
            self._stop = (len(self._switchboard.files) == 0)

    return EmptyingRunner()



class _Bag:
    def __init__(self, **kws):
        for key, value in kws.items():
            setattr(self, key, value)


def get_queue_messages(queue):
    """Return and clear all the messages in the given queue.

    :param queue: An ISwitchboard or a string naming a queue.
    :return: A list of 2-tuples where each item contains the message and
        message metadata.
    """
    if isinstance(queue, basestring):
        queue = Switchboard(queue)
    messages = []
    for filebase in queue.files:
        msg, msgdata = queue.dequeue(filebase)
        messages.append(_Bag(msg=msg, msgdata=msgdata))
        queue.finish(filebase)
    return messages



def digest_mbox(mlist):
    """The mailing list's pending digest as a mailbox.

    :param mlist: The mailing list.
    :return: The mailing list's pending digest as a mailbox.
    """
    path = os.path.join(mlist.full_path, 'digest.mbox')
    return mailbox.mbox(path)



class TestableMaster(Master):
    """A testable master loop watcher."""

    def __init__(self, event):
        super(TestableMaster, self).__init__(
            restartable=False, config_file=config.filename)
        self._event = event
        self._started_kids = None

    def loop(self):
        """Wait until all the qrunners are actually running before looping."""
        starting_kids = set(self._kids)
        while starting_kids:
            for pid in self._kids:
                try:
                    os.kill(pid, 0)
                    starting_kids.remove(pid)
                except OSError, error:
                    if error.errno == errno.ESRCH:
                        # The child has not yet started.
                        pass
                    raise
        # Keeping a copy of all the started child processes for use by the
        # testing environment, even after all have exited.
        self._started_kids = set(self._kids)
        # Let the blocking thread know everything's running.
        self._event.set()
        super(TestableMaster, self).loop()

    @property
    def qrunner_pids(self):
        """The pids of all the child qrunner processes."""
        for pid in self._started_kids:
            yield pid



class SMTPServer:
    """An smtp server for testing."""

    host = 'localhost'
    port = 9025

    def __init__(self):
        self._messages = []
        self._queue = Queue()
        self._server = Server((self.host, self.port), self._queue)
        self._thread = threading.Thread(target=self._server.start)

    def start(self):
        """Start the smtp server in a thread."""
        self._thread.start()

    def stop(self):
        """Stop the smtp server."""
        smtpd = smtplib.SMTP()
        smtpd.connect(self.host, self.port)
        smtpd.docmd('EXIT')
        self.clear()
        # Wait for the thread to exit.
        self._thread.join()

    @property
    def messages(self):
        """Return all the messages received by the smtp server."""
        for message in self._messages:
            # See if there's anything waiting in the queue.
            try:
                message = self._queue.get_nowait()
            except Empty:
                pass
            else:
                self._messages.append(message)
            yield message
            
    def clear(self):
        """Clear all messages from the queue."""
        # Just throw these away.
        list(self._messages)
        self._messages = []
