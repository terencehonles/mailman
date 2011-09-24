================
Avoid duplicates
================

This handler implements several strategies to reduce the reception of
duplicate messages.  It does this by removing certain recipients from the list
of recipients calculated earlier.

    >>> mlist = create_list('_xtest@example.com')

Create some members we're going to use.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> address_a = user_manager.create_address('aperson@example.com')
    >>> address_b = user_manager.create_address('bperson@example.com')

    >>> from mailman.interfaces.member import MemberRole
    >>> member_a = mlist.subscribe(address_a, MemberRole.member)
    >>> member_b = mlist.subscribe(address_b, MemberRole.member)
    >>> # This is the message metadata dictionary as it would be produced by
    >>> # the CalcRecips handler.
    >>> recips = dict(
    ...     recipients=['aperson@example.com', 'bperson@example.com'])


Short circuiting
================

The module short-circuits if there are no recipients.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: A message of great import
    ...
    ... Something
    ... """)
    >>> msgdata = {}

    >>> handler = config.handlers['avoid-duplicates']
    >>> handler.process(mlist, msg, msgdata)
    >>> msgdata
    {}
    >>> print msg.as_string()
    From: aperson@example.com
    Subject: A message of great import
    <BLANKLINE>
    Something
    <BLANKLINE>


Suppressing the list copy
=========================

Members can elect not to receive a list copy of any message on which they are
explicitly named as a recipient.  This is done by setting their
``receive_list_copy`` preference to ``False``.  However, if they aren't
mentioned in one of the recipient headers (i.e. ``To``, ``CC``, ``Resent-To``,
or ``Resent-CC``), then they will get a list copy.

    >>> member_a.preferences.receive_list_copy = False
    >>> msg = message_from_string("""\
    ... From: Claire Person <cperson@example.com>
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = recips.copy()
    >>> handler.process(mlist, msg, msgdata)
    >>> sorted(msgdata['recipients'])
    [u'aperson@example.com', u'bperson@example.com']
    >>> print msg.as_string()
    From: Claire Person <cperson@example.com>
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>

If they're mentioned on the ``CC`` line, they won't get a list copy.

    >>> msg = message_from_string("""\
    ... From: Claire Person <cperson@example.com>
    ... CC: aperson@example.com
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = recips.copy()
    >>> handler.process(mlist, msg, msgdata)
    >>> sorted(msgdata['recipients'])
    [u'bperson@example.com']
    >>> print msg.as_string()
    From: Claire Person <cperson@example.com>
    CC: aperson@example.com
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>

But if they're mentioned on the ``CC`` line and have ``receive_list_copy`` set
to ``True`` (the default), then they still get a list copy.

    >>> msg = message_from_string("""\
    ... From: Claire Person <cperson@example.com>
    ... CC: bperson@example.com
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = recips.copy()
    >>> handler.process(mlist, msg, msgdata)
    >>> sorted(msgdata['recipients'])
    [u'aperson@example.com', u'bperson@example.com']
    >>> print msg.as_string()
    From: Claire Person <cperson@example.com>
    CC: bperson@example.com
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>

Other headers checked for recipients include the ``To``...

    >>> msg = message_from_string("""\
    ... From: Claire Person <cperson@example.com>
    ... To: aperson@example.com
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = recips.copy()
    >>> handler.process(mlist, msg, msgdata)
    >>> sorted(msgdata['recipients'])
    [u'bperson@example.com']
    >>> print msg.as_string()
    From: Claire Person <cperson@example.com>
    To: aperson@example.com
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>

... ``Resent-To`` ...

    >>> msg = message_from_string("""\
    ... From: Claire Person <cperson@example.com>
    ... Resent-To: aperson@example.com
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = recips.copy()
    >>> handler.process(mlist, msg, msgdata)
    >>> sorted(msgdata['recipients'])
    [u'bperson@example.com']
    >>> print msg.as_string()
    From: Claire Person <cperson@example.com>
    Resent-To: aperson@example.com
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>

...and ``Resent-CC`` headers.

    >>> msg = message_from_string("""\
    ... From: Claire Person <cperson@example.com>
    ... Resent-Cc: aperson@example.com
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = recips.copy()
    >>> handler.process(mlist, msg, msgdata)
    >>> sorted(msgdata['recipients'])
    [u'bperson@example.com']
    >>> print msg.as_string()
    From: Claire Person <cperson@example.com>
    Resent-Cc: aperson@example.com
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>
