=======
Digests
=======

Digests are a way for a user to receive list traffic in collections instead of
as individual messages when immediately posted.  There are several forms of
digests, although only two are currently supported: MIME digests and RFC 1153
(a.k.a. plain text) digests.

    >>> mlist = create_list('xtest@example.com')

This is a helper function used to iterate through all the accumulated digest
messages, in the order in which they were posted.  This makes it easier to
update the tests when we switch to a different mailbox format.
::

    >>> from mailman.testing.helpers import digest_mbox
    >>> from itertools import count
    >>> from string import Template

    >>> def message_factory():
    ...     for i in count(1):
    ...         text = Template("""\
    ... From: aperson@example.com
    ... To: xtest@example.com
    ... Subject: Test message $i
    ...
    ... Here is message $i
    ... """).substitute(i=i)
    ...         yield message_from_string(text)
    >>> message_factory = message_factory()


Short circuiting
================

When a message is posted to the mailing list, it is generally added to a
mailbox, unless the mailing list does not allow digests.

    >>> mlist.digestable = False
    >>> msg = next(message_factory)
    >>> process = config.handlers['to-digest'].process
    >>> process(mlist, msg, {})
    >>> sum(1 for msg in digest_mbox(mlist))
    0
    >>> digest_queue = config.switchboards['digest']
    >>> digest_queue.files
    []

...or they may allow digests but the message is already a digest.

    >>> mlist.digestable = True
    >>> process(mlist, msg, dict(isdigest=True))
    >>> sum(1 for msg in digest_mbox(mlist))
    0
    >>> digest_queue.files
    []


Sending a digest
================

For messages which are not digests, but which are posted to a digesting
mailing list, the messages will be stored until they reach a criteria
triggering the sending of the digest.  If none of those criteria are met, then
the message will just sit in the mailbox for a while.

    >>> mlist.digest_size_threshold = 10000
    >>> process(mlist, msg, {})
    >>> digest_queue.files
    []
    >>> digest = digest_mbox(mlist)
    >>> sum(1 for msg in digest)
    1
    >>> import os
    >>> os.remove(digest._path)

When the size of the digest mailbox reaches the maximum size threshold, a
marker message is placed into the digest runner's queue.  The digest is not
actually crafted by the handler.

    >>> mlist.digest_size_threshold = 1
    >>> mlist.volume = 2
    >>> mlist.next_digest_number = 10
    >>> size = 0
    >>> for msg in message_factory:
    ...     process(mlist, msg, {})
    ...     size += len(str(msg))
    ...     if size >= mlist.digest_size_threshold * 1024:
    ...         break

    >>> sum(1 for msg in digest_mbox(mlist))
    0
    >>> len(digest_queue.files)
    1

The digest has been moved to a unique file.

    >>> from mailman.utilities.mailbox import Mailbox
    >>> from mailman.testing.helpers import get_queue_messages
    >>> item = get_queue_messages('digest')[0]
    >>> for msg in Mailbox(item.msgdata['digest_path']):
    ...     print msg['subject']
    Test message 2
    Test message 3
    Test message 4
    Test message 5
    Test message 6
    Test message 7
    Test message 8
    Test message 9

Digests are actually crafted and sent by a separate digest runner.
