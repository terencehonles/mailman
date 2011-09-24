=========
Digesting
=========

Mailman crafts and sends digests by a separate digest runner process.  This
starts by a number of messages being posted to the mailing list.
::

    >>> mlist = create_list('test@example.com')
    >>> mlist.digest_size_threshold = 0.6
    >>> mlist.volume = 1
    >>> mlist.next_digest_number = 1

    >>> from string import Template
    >>> process = config.handlers['to-digest'].process

    >>> def fill_digest():
    ...     size = 0
    ...     for i in range(1, 5):
    ...         text = Template("""\
    ... From: aperson@example.com
    ... To: xtest@example.com
    ... Subject: Test message $i
    ... List-Post: <test@example.com>
    ...
    ... Here is message $i
    ... """).substitute(i=i)
    ...         msg = message_from_string(text)
    ...         process(mlist, msg, {})
    ...         size += len(text)
    ...         if size >= mlist.digest_size_threshold * 1024:
    ...             break

    >>> fill_digest()

The runner gets kicked off when a marker message gets dropped into the digest
queue.  The message metadata points to the mailbox file containing the
messages to put in the digest.
::

    >>> digestq = config.switchboards['digest']
    >>> len(digestq.files)
    1

    >>> from mailman.testing.helpers import get_queue_messages
    >>> entry = get_queue_messages('digest')[0]

The marker message is empty.

    >>> print entry.msg.as_string()

But the message metadata has a reference to the digest file.
::

    >>> dump_msgdata(entry.msgdata)
    _parsemsg    : False
    digest_number: 1
    digest_path  : .../lists/test@example.com/digest.1.1.mmdf
    listname     : test@example.com
    version      : 3
    volume       : 1

    # Put the messages back in the queue for the runner to handle.
    >>> filebase = digestq.enqueue(entry.msg, entry.msgdata)

There are 4 messages in the digest.

    >>> from mailman.utilities.mailbox import Mailbox
    >>> sum(1 for item in Mailbox(entry.msgdata['digest_path']))
    4

When the runner runs, it processes the digest mailbox, crafting both the plain
text (RFC 1153) digest and the MIME digest.

    >>> from mailman.runners.digest import DigestRunner
    >>> from mailman.testing.helpers import make_testable_runner
    >>> runner = make_testable_runner(DigestRunner)
    >>> runner.run()

The digest runner places both digests into the virgin queue for final
delivery.

    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    2

The MIME digest is a multipart, and the RFC 1153 digest is the other one.
::

    >>> def mime_rfc1153(messages):
    ...     if messages[0].msg.is_multipart():
    ...         return messages[0], messages[1]
    ...     return messages[1], messages[0]

    >>> mime, rfc1153 = mime_rfc1153(messages)

The MIME digest has lots of good stuff, all contained in the multipart.

    >>> print mime.msg.as_string()
    Content-Type: multipart/mixed; boundary="===============...=="
    MIME-Version: 1.0
    From: test-request@example.com
    Subject: Test Digest, Vol 1, Issue 1
    To: test@example.com
    Reply-To: test@example.com
    Date: ...
    Message-ID: ...
    <BLANKLINE>
    --===============...==
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    Content-Description: Test Digest, Vol 1, Issue 1
    <BLANKLINE>
    Send Test mailing list submissions to
        test@example.com
    <BLANKLINE>
    To subscribe or unsubscribe via the World Wide Web, visit
        http://lists.example.com/listinfo/test@example.com
    or, via email, send a message with subject or body 'help' to
        test-request@example.com
    <BLANKLINE>
    You can reach the person managing the list at
        test-owner@example.com
    <BLANKLINE>
    When replying, please edit your Subject line so it is more specific
    than "Re: Contents of Test digest..."
    <BLANKLINE>
    --===============...==
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    Content-Description: Today's Topics (4 messages)
    <BLANKLINE>
    Today's Topics:
    <BLANKLINE>
       1. Test message 1 (aperson@example.com)
       2. Test message 2 (aperson@example.com)
       3. Test message 3 (aperson@example.com)
       4. Test message 4 (aperson@example.com)
    <BLANKLINE>
    --===============...==
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@example.com
    To: xtest@example.com
    Subject: Test message 1
    List-Post: <test@example.com>
    <BLANKLINE>
    Here is message 1
    <BLANKLINE>
    --===============...==
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@example.com
    To: xtest@example.com
    Subject: Test message 2
    List-Post: <test@example.com>
    <BLANKLINE>
    Here is message 2
    <BLANKLINE>
    --===============...==
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@example.com
    To: xtest@example.com
    Subject: Test message 3
    List-Post: <test@example.com>
    <BLANKLINE>
    Here is message 3
    <BLANKLINE>
    --===============...==
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@example.com
    To: xtest@example.com
    Subject: Test message 4
    List-Post: <test@example.com>
    <BLANKLINE>
    Here is message 4
    <BLANKLINE>
    --===============...==
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    Content-Description: Digest Footer
    <BLANKLINE>
    _______________________________________________
    Test mailing list
    test@example.com
    http://lists.example.com/listinfo/test@example.com
    <BLANKLINE>
    --===============...==--

The RFC 1153 contains the digest in a single plain text message.

    >>> print rfc1153.msg.as_string()
    From: test-request@example.com
    Subject: Test Digest, Vol 1, Issue 1
    To: test@example.com
    Reply-To: test@example.com
    Date: ...
    Message-ID: ...
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    Send Test mailing list submissions to
        test@example.com
    <BLANKLINE>
    To subscribe or unsubscribe via the World Wide Web, visit
        http://lists.example.com/listinfo/test@example.com
    or, via email, send a message with subject or body 'help' to
        test-request@example.com
    <BLANKLINE>
    You can reach the person managing the list at
        test-owner@example.com
    <BLANKLINE>
    When replying, please edit your Subject line so it is more specific
    than "Re: Contents of Test digest..."
    <BLANKLINE>
    <BLANKLINE>
    Today's Topics:
    <BLANKLINE>
       1. Test message 1 (aperson@example.com)
       2. Test message 2 (aperson@example.com)
       3. Test message 3 (aperson@example.com)
       4. Test message 4 (aperson@example.com)
    <BLANKLINE>
    <BLANKLINE>
    ----------------------------------------------------------------------
    <BLANKLINE>
    From: aperson@example.com
    Subject: Test message 1
    To: xtest@example.com
    Message-ID: ...
    <BLANKLINE>
    Here is message 1
    <BLANKLINE>
    ------------------------------
    <BLANKLINE>
    From: aperson@example.com
    Subject: Test message 2
    To: xtest@example.com
    Message-ID: ...
    <BLANKLINE>
    Here is message 2
    <BLANKLINE>
    ------------------------------
    <BLANKLINE>
    From: aperson@example.com
    Subject: Test message 3
    To: xtest@example.com
    Message-ID: ...
    <BLANKLINE>
    Here is message 3
    <BLANKLINE>
    ------------------------------
    <BLANKLINE>
    From: aperson@example.com
    Subject: Test message 4
    To: xtest@example.com
    Message-ID: ...
    <BLANKLINE>
    Here is message 4
    <BLANKLINE>
    ------------------------------
    <BLANKLINE>
    _______________________________________________
    Test mailing list
    test@example.com
    http://lists.example.com/listinfo/test@example.com
    <BLANKLINE>
    <BLANKLINE>
    End of Test Digest, Vol 1, Issue 1
    **********************************
    <BLANKLINE>


Internationalized digests
=========================

When messages come in with a content-type character set different than that of
the list's preferred language, recipients will get an internationalized
digest.  French is not enabled by default site-wide, so enable that now.
::

    # Simulate the site administrator setting the default server language to
    # French in the configuration file.  Without this, the English template
    # will be found and the masthead won't be translated.
    >>> config.push('french', """
    ... [mailman]
    ... default_language: fr
    ... """)

    >>> mlist.preferred_language =  'fr'
    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: test@example.com
    ... Subject: =?iso-2022-jp?b?GyRCMGxIVhsoQg==?=
    ... MIME-Version: 1.0
    ... Content-Type: text/plain; charset=iso-2022-jp
    ... Content-Transfer-Encoding: 7bit
    ...
    ... \x1b$B0lHV\x1b(B
    ... """)

Set the digest threshold to zero so that the digests will be sent immediately.

    >>> mlist.digest_size_threshold = 0
    >>> process(mlist, msg, {})

The marker message is sitting in the digest queue.

    >>> len(digestq.files)
    1
    >>> entry = get_queue_messages('digest')[0]
    >>> dump_msgdata(entry.msgdata)
    _parsemsg    : False
    digest_number: 2
    digest_path  : .../lists/test@example.com/digest.1.2.mmdf
    listname     : test@example.com
    version      : 3
    volume       : 1

The digest runner runs a loop, placing the two digests into the virgin queue.

    # Put the messages back in the queue for the runner to handle.
    >>> filebase = digestq.enqueue(entry.msg, entry.msgdata)
    >>> runner.run()
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    2

One of which is the MIME digest and the other of which is the RFC 1153 digest.

    >>> mime, rfc1153 = mime_rfc1153(messages)

You can see that the digests contain a mix of French and Japanese.

    >>> print mime.msg.as_string()
    Content-Type: multipart/mixed; boundary="===============...=="
    MIME-Version: 1.0
    From: test-request@example.com
    Subject: Groupe Test, Vol. 1, Parution 2
    To: test@example.com
    Reply-To: test@example.com
    Date: ...
    Message-ID: ...
    <BLANKLINE>
    --===============...==
    Content-Type: text/plain; charset="iso-8859-1"
    MIME-Version: 1.0
    Content-Transfer-Encoding: quoted-printable
    Content-Description: Groupe Test, Vol. 1, Parution 2
    <BLANKLINE>
    Envoyez vos messages pour la liste Test =E0
        test@example.com
    <BLANKLINE>
    Pour vous (d=E9s)abonner par le web, consultez
        http://lists.example.com/listinfo/test@example.com
    <BLANKLINE>
    ou, par courriel, envoyez un message avec =AB=A0help=A0=BB dans le corps ou
    dans le sujet =E0
        test-request@example.com
    <BLANKLINE>
    Vous pouvez contacter l'administrateur de la liste =E0 l'adresse
        test-owner@example.com
    <BLANKLINE>
    Si vous r=E9pondez, n'oubliez pas de changer l'objet du message afin
    qu'il soit plus sp=E9cifique que =AB=A0Re: Contenu du groupe de Test...=A0=
    =BB
    --===============...==
    Content-Type: text/plain; charset="utf-8"
    MIME-Version: 1.0
    Content-Transfer-Encoding: base64
    Content-Description: Today's Topics (1 messages)
    <BLANKLINE>
    VGjDqG1lcyBkdSBqb3VyIDoKCiAgIDEuIOS4gOeVqiAoYXBlcnNvbkBleGFtcGxlLm9yZykK
    <BLANKLINE>
    --===============...==
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@example.org
    To: test@example.com
    Subject: =?iso-2022-jp?b?GyRCMGxIVhsoQg==?=
    MIME-Version: 1.0
    Content-Type: text/plain; charset=iso-2022-jp
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    一番
    <BLANKLINE>
    --===============...==
    Content-Type: text/plain; charset="iso-8859-1"
    MIME-Version: 1.0
    Content-Transfer-Encoding: quoted-printable
    Content-Description: =?utf-8?q?Pied_de_page_des_remises_group=C3=A9es?=
    <BLANKLINE>
    _______________________________________________
    Test mailing list
    test@example.com
    http://lists.example.com/listinfo/test@example.com
    <BLANKLINE>
    --===============...==--

The RFC 1153 digest will be encoded in UTF-8 since it contains a mixture of
French and Japanese characters.

    >>> print rfc1153.msg.as_string()
    From: test-request@example.com
    Subject: Groupe Test, Vol. 1, Parution 2
    To: test@example.com
    Reply-To: test@example.com
    Date: ...
    Message-ID: ...
    MIME-Version: 1.0
    Content-Type: text/plain; charset="utf-8"
    Content-Transfer-Encoding: base64
    <BLANKLINE>
    RW52b...
    <BLANKLINE>

The content can be decoded to see the actual digest text.
::

    # We must display the repr of the decoded value because doctests cannot
    # handle the non-ascii characters.
    >>> [repr(line)
    ...  for line in rfc1153.msg.get_payload(decode=True).splitlines()]
    ["'Envoyez vos messages pour la liste Test \\xc3\\xa0'",
    "'\\ttest@example.com'",
    "''",
    "'Pour vous (d\\xc3\\xa9s)abonner par le web, consultez'",
    "'\\thttp://lists.example.com/listinfo/test@example.com'",
    "''",
    "'ou, par courriel, envoyez un message avec \\xc2\\xab\\xc2\\xa0...
    "'dans le sujet \\xc3\\xa0'",
    "'\\ttest-request@example.com'",
    "''",
    '"Vous pouvez contacter l\'administrateur de la liste \\xc3\\xa0 ...
    "'\\ttest-owner@example.com'",
    "''",
    '"Si vous r\\xc3\\xa9pondez, n\'oubliez pas de changer l\'objet du ...
    '"qu\'il soit plus sp\\xc3\\xa9cifique que \\xc2\\xab\\xc2\\xa0Re: ...
    "''",
    "'Th\\xc3\\xa8mes du jour :'",
    "''",
    "'   1. \\xe4\\xb8\\x80\\xe7\\x95\\xaa (aperson@example.org)'",
    "''",
    "''",
    "'---------------------------------------------------------------------...
    "''",
    "'From: aperson@example.org'",
    "'Subject: \\xe4\\xb8\\x80\\xe7\\x95\\xaa'",
    "'To: test@example.com'",
    "'Message-ID: ...
    "'Content-Type: text/plain; charset=iso-2022-jp'",
    "''",
    "'\\xe4\\xb8\\x80\\xe7\\x95\\xaa'",
    "''",
    "'------------------------------'",
    "''",
    "'_______________________________________________'",
    "'Test mailing list'",
    "'test@example.com'",
    "'http://lists.example.com/listinfo/test@example.com'",
    "''",
    "''",
    "'Fin de Groupe Test, Vol. 1, Parution 2'",
    "'**************************************'"]

     >>> config.pop('french')


Digest delivery
===============

A mailing list's members can choose to receive normal delivery, plain text
digests, or MIME digests.
::

    >>> len(get_queue_messages('virgin'))
    0

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> from mailman.interfaces.member import DeliveryMode, MemberRole
    >>> def subscribe(email, mode):
    ...     address = user_manager.create_address(email)
    ...     member = mlist.subscribe(address, MemberRole.member)
    ...     member.preferences.delivery_mode = mode
    ...     return member

Two regular delivery members subscribe to the mailing list.

    >>> member_1 = subscribe('uperson@example.com', DeliveryMode.regular)
    >>> member_2 = subscribe('vperson@example.com', DeliveryMode.regular)

Two MIME digest members subscribe to the mailing list.

    >>> member_3 = subscribe('wperson@example.com', DeliveryMode.mime_digests)
    >>> member_4 = subscribe('xperson@example.com', DeliveryMode.mime_digests)

One RFC 1153 digest member subscribes to the mailing list.

    >>> member_5 = subscribe(
    ...     'yperson@example.com', DeliveryMode.plaintext_digests)
    >>> member_6 = subscribe(
    ...     'zperson@example.com', DeliveryMode.plaintext_digests)

When a digest gets sent, the appropriate recipient list is chosen.

    >>> mlist.preferred_language = 'en'
    >>> mlist.digest_size_threshold = 0.5
    >>> fill_digest()
    >>> runner.run()

The digests are sitting in the virgin queue.  One of them is the MIME digest
and the other is the RFC 1153 digest.
::

    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    2

    >>> mime, rfc1153 = mime_rfc1153(messages)

Only wperson and xperson get the MIME digests.

    >>> sorted(mime.msgdata['recipients'])
    [u'wperson@example.com', u'xperson@example.com']

Only yperson and zperson get the RFC 1153 digests.

    >>> sorted(rfc1153.msgdata['recipients'])
    [u'yperson@example.com', u'zperson@example.com']

Now uperson decides that they would like to start receiving digests too.
::

    >>> member_1.preferences.delivery_mode = DeliveryMode.mime_digests
    >>> fill_digest()
    >>> runner.run()

    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    2

    >>> mime, rfc1153 = mime_rfc1153(messages)
    >>> sorted(mime.msgdata['recipients'])
    [u'uperson@example.com', u'wperson@example.com', u'xperson@example.com']

    >>> sorted(rfc1153.msgdata['recipients'])
    [u'yperson@example.com', u'zperson@example.com']

At this point, both uperson and wperson decide that they'd rather receive
regular deliveries instead of digests.  uperson would like to get any last
digest that may be sent so that she doesn't miss anything.  wperson does care
as much and does not want to receive one last digest.
::

    >>> mlist.send_one_last_digest_to(
    ...     member_1.address, member_1.preferences.delivery_mode)

    >>> member_1.preferences.delivery_mode = DeliveryMode.regular
    >>> member_3.preferences.delivery_mode = DeliveryMode.regular

    >>> fill_digest()
    >>> runner.run()

    >>> messages = get_queue_messages('virgin')
    >>> mime, rfc1153 = mime_rfc1153(messages)
    >>> sorted(mime.msgdata['recipients'])
    [u'uperson@example.com', u'xperson@example.com']

    >>> sorted(rfc1153.msgdata['recipients'])
    [u'yperson@example.com', u'zperson@example.com']

Since uperson has received their last digest, they will not get any more of
them.
::

    >>> fill_digest()
    >>> runner.run()

    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    2

    >>> mime, rfc1153 = mime_rfc1153(messages)
    >>> sorted(mime.msgdata['recipients'])
    [u'xperson@example.com']

    >>> sorted(rfc1153.msgdata['recipients'])
    [u'yperson@example.com', u'zperson@example.com']
