The switchboard
===============

The switchboard is subsystem that moves messages between queues.  Each
instance of a switchboard is responsible for one queue directory.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: _xtest@example.com
    ...
    ... A test message.
    ... """)

Create a switchboard by giving its queue name and directory.

    >>> import os
    >>> queue_directory = os.path.join(config.QUEUE_DIR, 'test')
    >>> from mailman.core.switchboard import Switchboard
    >>> switchboard = Switchboard('test', queue_directory)
    >>> print switchboard.name
    test
    >>> switchboard.queue_directory == queue_directory
    True

Here's a helper function for ensuring things work correctly.

    >>> def check_qfiles(directory=None):
    ...     if directory is None:
    ...         directory = queue_directory
    ...     files = {}
    ...     for qfile in os.listdir(directory):
    ...         root, ext = os.path.splitext(qfile)
    ...         files[ext] = files.get(ext, 0) + 1
    ...     if len(files) == 0:
    ...         print 'empty'
    ...     for ext in sorted(files):
    ...         print '{0}: {1}'.format(ext, files[ext])


Enqueing and dequeing
---------------------

The message can be enqueued with metadata specified in the passed in
dictionary.

    >>> filebase = switchboard.enqueue(msg)
    >>> check_qfiles()
    .pck: 1

To read the contents of a queue file, dequeue it.

    >>> msg, msgdata = switchboard.dequeue(filebase)
    >>> print msg.as_string()
    From: aperson@example.com
    To: _xtest@example.com
    <BLANKLINE>
    A test message.
    <BLANKLINE>
    >>> dump_msgdata(msgdata)
    _parsemsg: False
    version  : 3
    >>> check_qfiles()
    .bak: 1

To complete the dequeing process, removing all traces of the message file,
finish it (without preservation).

    >>> switchboard.finish(filebase)
    >>> check_qfiles()
    empty

When enqueing a file, you can provide additional metadata keys by using
keyword arguments.

    >>> filebase = switchboard.enqueue(msg, {'foo': 1}, bar=2)
    >>> msg, msgdata = switchboard.dequeue(filebase)
    >>> switchboard.finish(filebase)
    >>> dump_msgdata(msgdata)
    _parsemsg: False
    bar      : 2
    foo      : 1
    version  : 3

Keyword arguments override keys from the metadata dictionary.

    >>> filebase = switchboard.enqueue(msg, {'foo': 1}, foo=2)
    >>> msg, msgdata = switchboard.dequeue(filebase)
    >>> switchboard.finish(filebase)
    >>> dump_msgdata(msgdata)
    _parsemsg: False
    foo      : 2
    version  : 3


Iterating over files
--------------------

There are two ways to iterate over all the files in a switchboard's queue.
Normally, queue files end in .pck (for 'pickle') and the easiest way to
iterate over just these files is to use the .files attribute.

    >>> filebase_1 = switchboard.enqueue(msg, foo=1)
    >>> filebase_2 = switchboard.enqueue(msg, foo=2)
    >>> filebase_3 = switchboard.enqueue(msg, foo=3)
    >>> filebases = sorted((filebase_1, filebase_2, filebase_3))
    >>> sorted(switchboard.files) == filebases
    True
    >>> check_qfiles()
    .pck: 3

You can also use the .get_files() method if you want to iterate over all the
file bases for some other extension.

    >>> for filebase in switchboard.get_files():
    ...     msg, msgdata = switchboard.dequeue(filebase)
    >>> bakfiles = sorted(switchboard.get_files('.bak'))
    >>> bakfiles == filebases
    True
    >>> check_qfiles()
    .bak: 3
    >>> for filebase in switchboard.get_files('.bak'):
    ...     switchboard.finish(filebase)
    >>> check_qfiles()
    empty


Recovering files
----------------

Calling .dequeue() without calling .finish() leaves .bak backup files in
place.  These can be recovered when the switchboard is instantiated.

    >>> filebase_1 = switchboard.enqueue(msg, foo=1)
    >>> filebase_2 = switchboard.enqueue(msg, foo=2)
    >>> filebase_3 = switchboard.enqueue(msg, foo=3)
    >>> for filebase in switchboard.files:
    ...     msg, msgdata = switchboard.dequeue(filebase)
    ...     # Don't call .finish()
    >>> check_qfiles()
    .bak: 3
    >>> switchboard_2 = Switchboard('test', queue_directory, recover=True)
    >>> check_qfiles()
    .pck: 3

The files can be recovered explicitly.

    >>> for filebase in switchboard.files:
    ...     msg, msgdata = switchboard.dequeue(filebase)
    ...     # Don't call .finish()
    >>> check_qfiles()
    .bak: 3
    >>> switchboard.recover_backup_files()
    >>> check_qfiles()
    .pck: 3

But the files will only be recovered at most three times before they are
considered defective.  In order to prevent mail bombs and loops, once this
maximum is reached, the files will be preserved in the 'bad' queue.
::

    >>> for filebase in switchboard.files:
    ...     msg, msgdata = switchboard.dequeue(filebase)
    ...     # Don't call .finish()
    >>> check_qfiles()
    .bak: 3
    >>> switchboard.recover_backup_files()
    >>> check_qfiles()
    empty

    >>> bad = config.switchboards['bad']
    >>> check_qfiles(bad.queue_directory)
    .psv: 3


Clean up
--------

    >>> for file in os.listdir(bad.queue_directory):
    ...     os.remove(os.path.join(bad.queue_directory, file))
    >>> check_qfiles(bad.queue_directory)
    empty


Queue slices
------------

XXX Add tests for queue slices.
