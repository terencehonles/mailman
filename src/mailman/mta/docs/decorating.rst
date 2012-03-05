=======================
Personalized decoration
=======================

Personalized messages can be decorated by headers and footers containing
information specific to the recipient.

    >>> from mailman.mta.decorating import DecoratingDelivery
    >>> decorating = DecoratingDelivery()

Delivery strategies must implement the proper interface.

    >>> from mailman.interfaces.mta import IMailTransportAgentDelivery
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IMailTransportAgentDelivery, decorating)
    True


Decorations
===========

Decorations are added when the mailing list had a header and/or footer
defined, and the decoration handler is told to do personalized decorations.
We start by writing the site-global header and footer template.
::

    >>> import os, tempfile
    >>> template_dir = tempfile.mkdtemp()
    >>> site_dir = os.path.join(template_dir, 'site', 'en')
    >>> os.makedirs(site_dir)
    >>> config.push('templates', """
    ... [paths.testing]
    ... template_dir: {0}
    ... """.format(template_dir))

    >>> myheader_path = os.path.join(site_dir, 'myheader.txt')
    >>> with open(myheader_path, 'w') as fp:
    ...     print >> fp, """\
    ... Delivery address: $user_address
    ... Subscribed address: $user_delivered_to
    ... """
    >>> myfooter_path = os.path.join(site_dir, 'myfooter.txt')
    >>> with open(myfooter_path, 'w') as fp:
    ...     print >> fp, """\
    ... User name: $user_name
    ... Language: $user_language
    ... Options: $user_optionsurl
    ... """

Then create a mailing list which will use this header and footer.  Because
these are site-global templates, we can use a shorted URL.

    >>> mlist = create_list('test@example.com')
    >>> mlist.header_uri = 'mailman:///myheader.txt'
    >>> mlist.footer_uri = 'mailman:///myfooter.txt'

    >>> transaction.commit()

    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: test@example.com
    ... Subject: test one
    ... Message-ID: <aardvark>
    ...
    ... This is a test.
    ... """)

    >>> recipients = set([
    ...     'aperson@example.com',
    ...     'bperson@example.com',
    ...     'cperson@example.com',
    ...     ])

    >>> msgdata = dict(
    ...     recipients=recipients,
    ...     personalize=True,
    ...     )

More information is included when the recipient is a member of the mailing
list.
::

    >>> from zope.component import getUtility
    >>> from mailman.interfaces.member import MemberRole
    >>> from mailman.interfaces.usermanager import IUserManager
    >>> user_manager = getUtility(IUserManager)

    >>> anne = user_manager.create_user('aperson@example.com', 'Anne Person')
    >>> mlist.subscribe(list(anne.addresses)[0], MemberRole.member)
    <Member: Anne Person <aperson@example.com> ...

    >>> bart = user_manager.create_user('bperson@example.com', 'Bart Person')
    >>> mlist.subscribe(list(bart.addresses)[0], MemberRole.member)
    <Member: Bart Person <bperson@example.com> ...

    >>> cris = user_manager.create_user('cperson@example.com', 'Cris Person')
    >>> mlist.subscribe(list(cris.addresses)[0], MemberRole.member)
    <Member: Cris Person <cperson@example.com> ...

The decorations happen when the message is delivered.
::

    >>> decorating.deliver(mlist, msg, msgdata)
    {}
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> from operator import itemgetter
    >>> for message in sorted(messages, key=itemgetter('x-rcptto')):
    ...     print message.as_string()
    ...     print '----------'
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    Delivery address: aperson@example.com
    Subscribed address: aperson@example.com
    This is a test.
    User name: Anne Person
    Language: English (USA)
    Options: http://example.com/aperson@example.com
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: bperson@example.com
    <BLANKLINE>
    Delivery address: bperson@example.com
    Subscribed address: bperson@example.com
    This is a test.
    User name: Bart Person
    Language: English (USA)
    Options: http://example.com/bperson@example.com
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: cperson@example.com
    <BLANKLINE>
    Delivery address: cperson@example.com
    Subscribed address: cperson@example.com
    This is a test.
    User name: Cris Person
    Language: English (USA)
    Options: http://example.com/cperson@example.com
    ----------


Decorate only once
==================

Do not decorate a message twice.  Decorators must insert the ``decorated`` key
into the message metadata.
::

    >>> msgdata['nodecorate'] = True
    >>> decorating.deliver(mlist, msg, msgdata)
    {}
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> for message in sorted(messages, key=itemgetter('x-rcptto')):
    ...     print message.as_string()
    ...     print '----------'
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: bperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: cperson@example.com
    <BLANKLINE>
    This is a test.
    ----------

.. Clean up

    >>> config.pop('templates')
    >>> import shutil
    >>> shutil.rmtree(template_dir)
