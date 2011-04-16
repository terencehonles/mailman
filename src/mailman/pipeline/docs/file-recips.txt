===============
File recipients
===============

Mailman can calculate the recipients for a message from a Sendmail-style
include file.  This file must be called ``members.txt`` and it must live in
the list's data directory.

    >>> mlist = create_list('_xtest@example.com')


Short circuiting
================

If the message's metadata already has recipients, this handler immediately
returns.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... A message.
    ... """)
    >>> msgdata = {'recipients': 7}

    >>> handler = config.handlers['file-recipients']
    >>> handler.process(mlist, msg, msgdata)
    >>> print msg.as_string()
    From: aperson@example.com
    <BLANKLINE>
    A message.
    <BLANKLINE>
    >>> dump_msgdata(msgdata)
    recipients: 7


Missing file
============

The include file must live inside the list's data directory, under the name
``members.txt``.  If the file doesn't exist, the list of recipients will be
empty.

    >>> import os
    >>> file_path = os.path.join(mlist.data_path, 'members.txt')
    >>> open(file_path)
    Traceback (most recent call last):
    ...
    IOError: [Errno ...]
    No such file or directory: u'.../_xtest@example.com/members.txt'
    >>> msgdata = {}
    >>> handler.process(mlist, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    *Empty*


Existing file
=============

If the file exists, it contains a list of addresses, one per line.  These
addresses are returned as the set of recipients.
::

    >>> fp = open(file_path, 'w')
    >>> try:
    ...     print >> fp, 'bperson@example.com'
    ...     print >> fp, 'cperson@example.com'
    ...     print >> fp, 'dperson@example.com'
    ...     print >> fp, 'eperson@example.com'
    ...     print >> fp, 'fperson@example.com'
    ...     print >> fp, 'gperson@example.com'
    ... finally:
    ...     fp.close()

    >>> msgdata = {}
    >>> handler.process(mlist, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    bperson@example.com
    cperson@example.com
    dperson@example.com
    eperson@example.com
    fperson@example.com
    gperson@example.com

However, if the sender of the original message is a member of the list and
their address is in the include file, the sender's address is *not* included
in the recipients list.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> address_1 = getUtility(IUserManager).create_address(
    ...     'cperson@example.com')

    >>> from mailman.interfaces.member import MemberRole
    >>> mlist.subscribe(address_1, MemberRole.member)
    <Member: cperson@example.com on _xtest@example.com as MemberRole.member>

    >>> msg = message_from_string("""\
    ... From: cperson@example.com
    ...
    ... A message.
    ... """)
    >>> msgdata = {}
    >>> handler.process(mlist, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    bperson@example.com
    dperson@example.com
    eperson@example.com
    fperson@example.com
    gperson@example.com
