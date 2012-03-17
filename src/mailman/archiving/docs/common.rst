=========
Archivers
=========

Mailman supports pluggable archivers, and it comes with several default
archivers.

    >>> mlist = create_list('test@example.com')
    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: test@example.com
    ... Subject: An archived message
    ... Message-ID: <12345>
    ... X-Message-ID-Hash: RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE
    ...
    ... Here is an archived message.
    ... """)

Archivers support an interface which provides the RFC 2369 ``List-Archive:``
header, and one that provides a *permalink* to the specific message object in
the archive.  This latter is appropriate for the message footer or for the RFC
5064 ``Archived-At:`` header.

Mailman defines a draft spec for how list servers and archivers can
interoperate.

    >>> archivers = {}
    >>> from operator import attrgetter
    >>> for archiver in sorted(config.archivers, key=attrgetter('name')):
    ...     print archiver.name
    ...     print '   ', archiver.list_url(mlist)
    ...     print '   ', archiver.permalink(mlist, msg)
    ...     archivers[archiver.name] = archiver
    mail-archive
        http://go.mail-archive.dev/test%40example.com
        http://go.mail-archive.dev/RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE
    mhonarc
        http://lists.example.com/.../test@example.com
        http://lists.example.com/.../RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE
    prototype
        http://lists.example.com
        http://lists.example.com/RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE


Sending the message to the archiver
===================================

The `prototype` archiver archives messages to a maildir.

    >>> import os
    >>> archivers['prototype'].archive_message(mlist, msg)
    >>> archive_path = os.path.join(
    ...     config.ARCHIVE_DIR, 'prototype', mlist.fqdn_listname, 'new')
    >>> len(os.listdir(archive_path))
    1


The Mail-Archive.com
====================

`The Mail Archive`_ is a public archiver that can be used to archive message
for free.  Mailman comes with a plugin for this archiver; by enabling it
messages to public lists will get sent there automatically.

    >>> archiver = archivers['mail-archive']
    >>> print archiver.list_url(mlist)
    http://go.mail-archive.dev/test%40example.com
    >>> print archiver.permalink(mlist, msg)
    http://go.mail-archive.dev/RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE

To archive the message, the archiver actually mails the message to a special
address at The Mail Archive.  The message gets no header or footer decoration.
::

    >>> archiver.archive_message(mlist, msg)

    >>> from mailman.runners.outgoing import OutgoingRunner
    >>> from mailman.testing.helpers import make_testable_runner
    >>> outgoing = make_testable_runner(OutgoingRunner, 'out')
    >>> outgoing.run()

    >>> from operator import itemgetter
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1

    >>> print messages[0].as_string()
    From: aperson@example.org
    To: test@example.com
    Subject: An archived message
    Message-ID: <12345>
    X-Message-ID-Hash: RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE
    X-Peer: 127.0.0.1:...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: archive@mail-archive.dev
    <BLANKLINE>
    Here is an archived message.

    >>> smtpd.clear()

However, if the mailing list is not public, the message will never be archived
at this service.

    >>> mlist.archive_private = True
    >>> print archiver.list_url(mlist)
    None
    >>> print archiver.permalink(mlist, msg)
    None
    >>> archiver.archive_message(mlist, msg)
    >>> list(smtpd.messages)
    []

Additionally, this archiver can handle malformed ``Message-IDs``.
::

    >>> from mailman.utilities.email import add_message_hash
    >>> mlist.archive_private = False
    >>> del msg['message-id']
    >>> del msg['x-message-id-hash']
    >>> msg['Message-ID'] = '12345>'
    >>> add_message_hash(msg)
    >>> print archiver.permalink(mlist, msg)
    http://go.mail-archive.dev/YJIGBYRWZFG5LZEBQ7NR25B5HBR2BVD6

    >>> del msg['message-id']
    >>> del msg['x-message-id-hash']
    >>> msg['Message-ID'] = '<12345'
    >>> add_message_hash(msg)
    >>> print archiver.permalink(mlist, msg)
    http://go.mail-archive.dev/XUFFJNJ2P2WC4NDPQRZFDJMV24POP64B

    >>> del msg['message-id']
    >>> del msg['x-message-id-hash']
    >>> msg['Message-ID'] = '12345'
    >>> add_message_hash(msg)
    >>> print archiver.permalink(mlist, msg)
    http://go.mail-archive.dev/RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE

    >>> del msg['message-id']
    >>> del msg['x-message-id-hash']
    >>> add_message_hash(msg)
    >>> msg['Message-ID'] = '    12345    '
    >>> add_message_hash(msg)
    >>> print archiver.permalink(mlist, msg)
    http://go.mail-archive.dev/RSZCG7IGPHFIRW3EMTVMMDNJMNCVCOLE


MHonArc
=======

A MHonArc_ archiver is also available.

    >>> archiver = archivers['mhonarc']
    >>> print archiver.name
    mhonarc

Messages sent to a local MHonArc instance are added to its archive via a
subprocess call.

    >>> from mailman.testing.helpers import LogFileMark
    >>> mark = LogFileMark('mailman.archiver')
    >>> archiver.archive_message(mlist, msg)
    >>> print 'LOG:', mark.readline()
    LOG: ... /usr/bin/mhonarc
         -add
         -dbfile .../test@example.com.mbox/mhonarc.db
         -outdir .../mhonarc/test@example.com
         -stderr .../logs/mhonarc
         -stdout .../logs/mhonarc -spammode -umask 022


.. _`The Mail Archive`: http://www.mail-archive.com
.. _MHonArc: http://www.mhonarc.org
