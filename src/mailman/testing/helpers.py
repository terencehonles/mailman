# Copyright (C) 2008-2009 by the Free Software Foundation, Inc.
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

"""Various test helpers."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'TestableMaster',
    'digest_mbox',
    'get_lmtp_client',
    'get_queue_messages',
    'make_testable_runner',
    'wait_for_webservice',
    ]


import os
import time
import errno
import signal
import socket
import logging
import smtplib
import datetime
import threading

from mailman.bin.master import Loop as Master
from mailman.config import config
from mailman.utilities.mailbox import Mailbox


STARTUP_WAIT = datetime.timedelta(seconds=5)
log = logging.getLogger('mailman.debug')



def make_testable_runner(runner_class, name=None):
    """Create a queue runner that runs until its queue is empty.

    :param runner_class: The queue runner's class.
    :type runner_class: class
    :param name: Optional queue name; if not given, it is calculated from the
        class name.
    :type name: string or None
    :return: A runner instance.
    """

    if name is None:
        assert runner_class.__name__.endswith('Runner'), (
            'Unparseable runner class name: %s' % runner_class.__name__)
        name = runner_class.__name__[:-6].lower()

    class EmptyingRunner(runner_class):
        """Stop processing when the queue is empty."""

        def __init__(self, *args, **kws):
            super(EmptyingRunner, self).__init__(*args, **kws)
            # We know it's an EmptyingRunner, so really we want to see the
            # super class in the log files.
            self.__class__.__name__ = runner_class.__name__

        def _do_periodic(self):
            """Stop when the queue is empty."""
            self._stop = (len(self.switchboard.files) == 0)

    return EmptyingRunner(name)



class _Bag:
    def __init__(self, **kws):
        for key, value in kws.items():
            setattr(self, key, value)


def get_queue_messages(queue_name):
    """Return and clear all the messages in the given queue.

    :param queue_name: A string naming a queue.
    :return: A list of 2-tuples where each item contains the message and
        message metadata.
    """
    queue = config.switchboards[queue_name]
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
    path = os.path.join(mlist.data_path, 'digest.mmdf')
    return Mailbox(path)



class TestableMaster(Master):
    """A testable master loop watcher."""

    def __init__(self, start_check=None):
        """Create a testable master loop watcher.

        :param start_check: Optional callable used to check whether everything
            is running as the test expects.  Called in `loop()` in the
            subthread before the event is set.  The callback should block
            until the pass condition is set.
        :type start_check: Callable taking no arguments, returning nothing.
        """
        super(TestableMaster, self).__init__(
            restartable=False, config_file=config.filename)
        self.start_check = start_check
        self.event = threading.Event()
        self.thread = threading.Thread(target=self.loop)
        self.thread.daemon = True
        self._started_kids = None

    def _pause(self):
        """See `Master`."""
        # No-op this because the tests generally do not signal the master,
        # which would mean the signal.pause() never exits.
        pass

    def start(self, *qrunners):
        """Start the master."""
        self.start_qrunners(qrunners)
        self.thread.start()
        # Wait until all the children are definitely started.
        self.event.wait()

    def stop(self):
        """Stop the master by killing all the children."""
        for pid in self.qrunner_pids:
            os.kill(pid, signal.SIGTERM)
        self.cleanup()
        self.thread.join()

    def loop(self):
        """Wait until all the qrunners are actually running before looping."""
        starting_kids = set(self._kids)
        while starting_kids:
            for pid in self._kids:
                try:
                    os.kill(pid, 0)
                    starting_kids.remove(pid)
                except OSError as error:
                    if error.errno == errno.ESRCH:
                        # The child has not yet started.
                        pass
                    raise
        # Keeping a copy of all the started child processes for use by the
        # testing environment, even after all have exited.
        self._started_kids = set(self._kids)
        # If there are extra conditions to check, do it now.
        if self.start_check is not None:
            self.start_check()
        # Let the blocking thread know everything's running.
        self.event.set()
        super(TestableMaster, self).loop()

    @property
    def qrunner_pids(self):
        """The pids of all the child qrunner processes."""
        for pid in self._started_kids:
            yield pid



class LMTP(smtplib.SMTP):
    """Like a normal SMTP client, but for LMTP."""
    def lhlo(self, name=''):
        self.putcmd('lhlo', name or self.local_hostname)
        code, msg = self.getreply()
        self.helo_resp = msg
        return code, msg


def get_lmtp_client():
    """Return a connected LMTP client."""
    # It's possible the process has started but is not yet accepting
    # connections.  Wait a little while.
    lmtp = LMTP()
    until = datetime.datetime.now() + STARTUP_WAIT
    while datetime.datetime.now() < until:
        try:
            response = lmtp.connect(
                config.mta.lmtp_host, int(config.mta.lmtp_port))
            print response
            return lmtp
        except socket.error, error:
            if error[0] == errno.ECONNREFUSED:
                time.sleep(0.5)
            else:
                raise
    else:
        raise RuntimeError('Connection refused')



def wait_for_webservice():
    """Wait for the REST server to start serving requests."""
    # Time out after approximately 3 seconds.
    for count in range(30):
        try:
            socket.socket().connect((config.webservice.hostname,
                                     int(config.webservice.port)))
        except socket.error:
            time.sleep(0.1)
        else:
            break
