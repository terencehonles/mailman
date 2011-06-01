=======
Runners
=======

The *runners* are the processes that perform long-running tasks, such as
moving messages around the Mailman queues.  Some runners don't manage queues,
such as the LMTP and REST API handling runners.  Each runner that manages a
queue directory though, is responsible for a slice of the hash space.  It
processes all the files in its slice, sleeps a little while, then wakes up and
runs through its queue files again.


Basic architecture
==================

The basic architecture of runner is implemented in the base class that all
runners inherit from.  This base class implements a ``.run()`` method that
runs continuously in a loop until the ``.stop()`` method is called.

    >>> mlist = create_list('test@example.com')

Here is a very simple derived runner class.  Runners use a configuration
section in the configuration files to determine run characteristics, such as
the queue directory to use.  Here we push a configuration section for the test
runner.
::

    >>> config.push('test-runner', """
    ... [runner.test]
    ... max_restarts: 1
    ... """)

    >>> from mailman.core.runner import Runner
    >>> class TestableRunner(Runner):
    ...     def _dispose(self, mlist, msg, msgdata):
    ...         self.msg = msg
    ...         self.msgdata = msgdata
    ...         return False
    ...
    ...     def _do_periodic(self):
    ...         self.stop()
    ...
    ...     def _snooze(self, filecnt):
    ...         return

    >>> runner = TestableRunner('test')

This runner doesn't do much except run once, storing the message and metadata
on instance variables.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ...
    ... A test message.
    ... """)
    >>> switchboard = config.switchboards['test']
    >>> filebase = switchboard.enqueue(msg, listname=mlist.fqdn_listname,
    ...                                foo='yes', bar='no')
    >>> runner.run()
    >>> print runner.msg.as_string()
    From: aperson@example.com
    To: test@example.com
    <BLANKLINE>
    A test message.
    <BLANKLINE>
    >>> dump_msgdata(runner.msgdata)
    _parsemsg: False
    bar      : no
    foo      : yes
    lang     : en
    listname : test@example.com
    version  : 3

XXX More of the Runner API should be tested.
