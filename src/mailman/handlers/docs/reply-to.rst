================
Reply-to munging
================

Messages that flow through the global pipeline get their headers *cooked*,
which basically means that their headers go through several mostly unrelated
transformations.  Some headers get added, others get changed.  Some of these
changes depend on mailing list settings and others depend on how the message
is getting sent through the system.  We'll take things one-by-one.

    >>> mlist = create_list('_xtest@example.com')

*Reply-to munging* refers to the behavior where a mailing list can be
configured to change or augment an existing ``Reply-To`` header in a message
posted to the list.  Reply-to munging is fairly controversial, with arguments
made either for or against munging.

The Mailman developers, and I believe the majority consensus is to do no
reply-to munging, under several principles.  Primarily, most reply-to munging
is requested by people who do not have both a `Reply` and `Reply All` button
on their mail reader.  If you do not munge ``Reply-To``, then these buttons
will work properly, but if you munge the header, it is impossible for these
buttons to work right, because both will reply to the list.  This leads to
unfortunate accidents where a private message is accidentally posted to the
entire list.

However, Mailman gives list owners the option to do reply-To munging anyway,
mostly as a way to shut up the really vocal minority who seem to insist on
this mis-feature.


Reply to list
=============

A list can be configured to add a ``Reply-To`` header pointing back to the
mailing list's posting address.  If there's no ``Reply-To`` header in the
original message, the list's posting address simply gets inserted.
::

    >>> from mailman.interfaces.mailinglist import ReplyToMunging
    >>> mlist.reply_goes_to_list = ReplyToMunging.point_to_list
    >>> mlist.preferred_language = 'en'
    >>> mlist.description = ''
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... """)

    >>> from mailman.handlers.cook_headers import process
    >>> process(mlist, msg, {})
    >>> len(msg.get_all('reply-to'))
    1
    >>> print msg['reply-to']
    _xtest@example.com

It's also possible to strip any existing ``Reply-To`` header first, before
adding the list's posting address.

    >>> mlist.first_strip_reply_to = True
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Reply-To: bperson@example.com
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> len(msg.get_all('reply-to'))
    1
    >>> print msg['reply-to']
    _xtest@example.com

If you don't first strip the header, then the list's posting address will just
get appended to whatever the original version was.

    >>> mlist.first_strip_reply_to = False
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Reply-To: bperson@example.com
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> len(msg.get_all('reply-to'))
    1
    >>> print msg['reply-to']
    bperson@example.com, _xtest@example.com


Explicit Reply-To
=================

The list can also be configured to have an explicit ``Reply-To`` header.

    >>> mlist.reply_goes_to_list = ReplyToMunging.explicit_header
    >>> mlist.reply_to_address = 'my-list@example.com'
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> len(msg.get_all('reply-to'))
    1
    >>> print msg['reply-to']
    my-list@example.com

And as before, it's possible to either strip any existing ``Reply-To``
header...

    >>> mlist.first_strip_reply_to = True
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Reply-To: bperson@example.com
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> len(msg.get_all('reply-to'))
    1
    >>> print msg['reply-to']
    my-list@example.com

...or not.

    >>> mlist.first_strip_reply_to = False
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Reply-To: bperson@example.com
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> len(msg.get_all('reply-to'))
    1
    >>> print msg['reply-to']
    my-list@example.com, bperson@example.com
