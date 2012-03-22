# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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
    'LogFileMark',
    'TestableMaster',
    'body_line_iterator',
    'call_api',
    'digest_mbox',
    'event_subscribers',
    'get_lmtp_client',
    'get_queue_messages',
    'make_testable_runner',
    'reset_the_world',
    'specialized_message_from_string',
    'subscribe',
    'wait_for_webservice',
    ]


import os
import json
import time
import errno
import signal
import socket
import logging
import smtplib
import datetime
import threading

from base64 import b64encode
from contextlib import contextmanager
from email import message_from_string
from httplib2 import Http
from lazr.config import as_timedelta
from urllib import urlencode
from urllib2 import HTTPError
from zope import event
from zope.component import getUtility

from mailman.bin.master import Loop as Master
from mailman.config import config
from mailman.email.message import Message
from mailman.interfaces.member import MemberRole
from mailman.interfaces.messages import IMessageStore
from mailman.interfaces.styles import IStyleManager
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.mailbox import Mailbox



def make_testable_runner(runner_class, name=None, predicate=None):
    """Create a runner that runs until its queue is empty.

    :param runner_class: The runner class.
    :type runner_class: class
    :param name: Optional queue name; if not given, it is calculated from the
        class name.
    :type name: string or None
    :param predicate: Optional alternative predicate for deciding when to stop
        the runner.  When None (the default) it stops when the queue is empty.
    :type predicate: callable that gets one argument, the queue runner.
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
            if predicate is None:
                self._stop = (len(self.switchboard.files) == 0)
            else:
                self._stop = predicate(self)

    return EmptyingRunner(name)



class _Bag:
    def __init__(self, **kws):
        for key, value in kws.items():
            setattr(self, key, value)


def get_queue_messages(queue_name, sort_on=None):
    """Return and clear all the messages in the given queue.

    :param queue_name: A string naming a queue.
    :param sort_on: The message header to sort on.  If None (the default),
        no sorting is performed.
    :return: A list of 2-tuples where each item contains the message and
        message metadata.
    """
    queue = config.switchboards[queue_name]
    messages = []
    for filebase in queue.files:
        msg, msgdata = queue.dequeue(filebase)
        messages.append(_Bag(msg=msg, msgdata=msgdata))
        queue.finish(filebase)
    if sort_on is not None:
        messages.sort(key=lambda item: str(item.msg[sort_on]))
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

    def start(self, *runners):
        """Start the master."""
        self.start_runners(runners)
        self.thread.start()
        # Wait until all the children are definitely started.
        self.event.wait()

    def stop(self):
        """Stop the master by killing all the children."""
        for pid in self.runner_pids:
            os.kill(pid, signal.SIGTERM)
        self.cleanup()
        self.thread.join()

    def loop(self):
        """Wait until all the runners are actually running before looping."""
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
    def runner_pids(self):
        """The pids of all the child runner processes."""
        for pid in self._started_kids:
            yield pid



class LMTP(smtplib.SMTP):
    """Like a normal SMTP client, but for LMTP."""
    def lhlo(self, name=''):
        self.putcmd('lhlo', name or self.local_hostname)
        code, msg = self.getreply()
        self.helo_resp = msg
        return code, msg


def get_lmtp_client(quiet=False):
    """Return a connected LMTP client."""
    # It's possible the process has started but is not yet accepting
    # connections.  Wait a little while.
    lmtp = LMTP()
    until = datetime.datetime.now() + as_timedelta(config.devmode.wait)
    while datetime.datetime.now() < until:
        try:
            response = lmtp.connect(
                config.mta.lmtp_host, int(config.mta.lmtp_port))
            if not quiet:
                print response
            return lmtp
        except socket.error as error:
            if error[0] == errno.ECONNREFUSED:
                time.sleep(0.1)
            else:
                raise
    else:
        raise RuntimeError('Connection refused')



def wait_for_webservice():
    """Wait for the REST server to start serving requests."""
    until = datetime.datetime.now() + as_timedelta(config.devmode.wait)
    while datetime.datetime.now() < until:
        try:
            socket.socket().connect((config.webservice.hostname,
                                    int(config.webservice.port)))
        except socket.error as error:
            if error[0] == errno.ECONNREFUSED:
                time.sleep(0.1)
            else:
                raise
        else:
            break
    else:
        raise RuntimeError('Connection refused')


def call_api(url, data=None, method=None, username=None, password=None):
    """'Call a URL with a given HTTP method and return the resulting object.

    The object will have been JSON decoded.

    :param url: The url to open, read, and print.
    :type url: string
    :param data: Data to use to POST to a URL.
    :type data: dict
    :param method: Alternative HTTP method to use.
    :type method: str
    :param username: The HTTP Basic Auth user name.  None means use the value
        from the configuration.
    :type username: str
    :param password: The HTTP Basic Auth password.  None means use the value
        from the configuration.
    :type username: str
    :return: The response object and the JSON decoded content, if there is
        any.  If not, the second tuple item will be None.
    :raises HTTPError: when a non-2xx return code is received.
    """
    headers = {}
    if data is not None:
        data = urlencode(data, doseq=True)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if method is None:
        if data is None:
            method = 'GET'
        else:
            method = 'POST'
    method = method.upper()
    basic_auth = '{0}:{1}'.format(
        (config.webservice.admin_user if username is None else username),
        (config.webservice.admin_pass if password is None else password))
    headers['Authorization'] = 'Basic ' + b64encode(basic_auth)
    response, content = Http().request(url, method, data, headers)
    # If we did not get a 2xx status code, make this look like a urllib2
    # exception, for backward compatibility with existing doctests.
    if response.status // 100 != 2:
        raise HTTPError(url, response.status, content, response, None)
    if len(content) == 0:
        return None, response
    # XXX Workaround http://bugs.python.org/issue10038
    content = unicode(content)
    return json.loads(content), response



@contextmanager
def event_subscribers(*subscribers):
    """Temporarily set the Zope event subscribers list.

    :param subscribers: A sequence of event subscribers.
    :type subscribers: sequence of callables, each receiving one argument, the
        event.
    """
    old_subscribers = event.subscribers[:]
    event.subscribers = list(subscribers)
    try:
        yield
    finally:
        event.subscribers[:] = old_subscribers



def subscribe(mlist, first_name, role=MemberRole.member):
    """Helper for subscribing a sample person to a mailing list."""
    user_manager = getUtility(IUserManager)
    email = '{0}person@example.com'.format(first_name[0].lower())
    full_name = '{0} Person'.format(first_name)
    person = user_manager.get_user(email)
    if person is None:
        address = user_manager.get_address(email)
        if address is None:
            person = user_manager.create_user(email, full_name)
            preferred_address = list(person.addresses)[0]
            mlist.subscribe(preferred_address, role)
        else:
            mlist.subscribe(address, role)
    else:
        preferred_address = list(person.addresses)[0]
        mlist.subscribe(preferred_address, role)
    config.db.commit()



def reset_the_world():
    """Reset everything:

    * Clear out the database
    * Remove all residual queue and digest files
    * Clear the message store
    * Reset the global style manager

    This should be as thorough a reset of the system as necessary to keep
    tests isolated.
    """
    # Reset the database between tests.
    config.db._reset()
    # Remove any digest files.
    for dirpath, dirnames, filenames in os.walk(config.LIST_DATA_DIR):
        for filename in filenames:
            if filename.endswith('.mmdf'):
                os.remove(os.path.join(dirpath, filename))
    # Remove all residual queue files.
    for dirpath, dirnames, filenames in os.walk(config.QUEUE_DIR):
        for filename in filenames:
            os.remove(os.path.join(dirpath, filename))
    # Clear out messages in the message store.
    message_store = getUtility(IMessageStore)
    for message in message_store.messages:
        message_store.delete_message(message['message-id'])
    config.db.commit()
    # Reset the global style manager.
    getUtility(IStyleManager).populate()



def specialized_message_from_string(unicode_text):
    """Parse text into a message object.

    This is specialized in the sense that an instance of Mailman's own Message
    object is returned, and this message object has an attribute
    `original_size` which is the pre-calculated size in bytes of the message's
    text representation.

    Also, the text must be ASCII-only unicode.
    """
    # This mimic what Switchboard.dequeue() does when parsing a message from
    # text into a Message instance.
    text = unicode_text.encode('ascii')
    original_size = len(text)
    message = message_from_string(text, Message)
    message.original_size = original_size
    return message



class LogFileMark:
    def __init__(self, log_name):
        self._log = logging.getLogger(log_name)
        self._filename = self._log.handlers[0].filename
        self._filepos = os.stat(self._filename).st_size

    def readline(self):
        with open(self._filename) as fp:
            fp.seek(self._filepos)
            return fp.readline()



# In Python 2.6, body_line_iterator() uses a cStringIO.StringIO() which cannot
# handle unicode.  In Python 2.7 this works fine.  I hate version checks but
# this is the easiest way to handle it.  OTOH, we could just use the manual
# way for all Python versions instead.
import sys
if sys.hexversion >= 0x2070000:
    from email.iterators import body_line_iterator
else:
    def body_line_iterator(msg, decode=False):
        payload = msg.get_payload(decode=decode)
        bytes_payload = payload.encode('utf-8')
        for line in bytes_payload.splitlines():
            yield line
