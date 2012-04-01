===============
Subject munging
===============

Messages that flow through the global pipeline get their headers *cooked*,
which basically means that their headers go through several mostly unrelated
transformations.  Some headers get added, others get changed.  Some of these
changes depend on mailing list settings and others depend on how the message
is getting sent through the system.  We'll take things one-by-one.

    >>> mlist = create_list('test@example.com')


Inserting a prefix
==================

Another thing header cooking does is *munge* the ``Subject`` header by
inserting the subject prefix for the list at the front.  If there's no subject
header in the original message, Mailman uses a canned default.  In order to do
subject munging, a mailing list must have a preferred language.
::

    >>> mlist.subject_prefix = '[XTest] '
    >>> mlist.preferred_language = 'en'
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... A message of great import.
    ... """)
    >>> msgdata = {}

    >>> from mailman.handlers.cook_headers import process
    >>> process(mlist, msg, msgdata)

The original subject header is stored in the message metadata.

    >>> msgdata['original_subject']
    u''
    >>> print msg['subject']
    [XTest] (no subject)

If the original message had a ``Subject`` header, then the prefix is inserted
at the beginning of the header's value.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: Something important
    ...
    ... A message of great import.
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msgdata['original_subject']
    Something important
    >>> print msg['subject']
    [XTest] Something important

``Subject`` headers are not munged for digest messages.
    
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: Something important
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, dict(isdigest=True))
    >>> print msg['subject']
    Something important

Nor are they munged for *fast tracked* messages, which are generally defined
as messages that Mailman crafts internally.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: Something important
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, dict(_fasttrack=True))
    >>> print msg['subject']
    Something important

If a ``Subject`` header already has a prefix, usually following a ``Re:``
marker, another one will not be added but the prefix will be moved to the
front of the header text.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: Re: [XTest] Something important
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest] Re: Something important

If the ``Subject`` header has a prefix at the front of the header text, that's
where it will stay.  This is called *new style* prefixing and is the only
option available in Mailman 3.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: [XTest] Re: Something important
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest] Re: Something important


Internationalized headers
=========================

Internationalization adds some interesting twists to the handling of subject
prefixes.  Part of what makes this interesting is the encoding of i18n headers
using RFC 2047, and lists whose preferred language is in a different character
set than the encoded header.

    >>> msg = message_from_string("""\
    ... Subject: =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest] =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=
    >>> unicode(msg['subject'])
    u'[XTest] \u30e1\u30fc\u30eb\u30de\u30f3'


Prefix numbers
==============

Subject prefixes support a placeholder for the numeric post id.  Every time a
message is posted to the mailing list, a *post id* gets incremented.  This is
a purely sequential integer that increases monotonically.  By added a ``%d``
placeholder to the subject prefix, this post id can be included in the prefix.

    >>> mlist.subject_prefix = '[XTest %d] '
    >>> mlist.post_id = 456
    >>> msg = message_from_string("""\
    ... Subject: Something important
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest 456] Something important

This works even when the message is a reply, except that in this case, the
numeric post id in the generated subject prefix is updated with the new post
id.

    >>> msg = message_from_string("""\
    ... Subject: [XTest 123] Re: Something important
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest 456] Re: Something important

If the ``Subject`` header had old style prefixing, the prefix is moved to the
front of the header text.

    >>> msg = message_from_string("""\
    ... Subject: Re: [XTest 123] Something important
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest 456] Re: Something important


And of course, the proper thing is done when posting id numbers are included
in the subject prefix, and the subject is encoded non-ASCII.

    >>> msg = message_from_string("""\
    ... Subject: =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest 456] =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=
    >>> unicode(msg['subject'])
    u'[XTest 456] \u30e1\u30fc\u30eb\u30de\u30f3'

Even more fun is when the internationalized ``Subject`` header already has a
prefix, possibly with a different posting number.

    >>> msg = message_from_string("""\
    ... Subject: [XTest 123] Re: =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest 456] Re: =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=

..
 # XXX This requires Python email patch #1681333 to succeed.
 #    >>> unicode(msg['subject'])
 #    u'[XTest 456] Re: \u30e1\u30fc\u30eb\u30de\u30f3'

As before, old style subject prefixes are re-ordered.

    >>> msg = message_from_string("""\
    ... Subject: Re: [XTest 123] =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest 456] Re:
      =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=

..
 # XXX This requires Python email patch #1681333 to succeed.
 #    >>> unicode(msg['subject'])
 #    u'[XTest 456] Re: \u30e1\u30fc\u30eb\u30de\u30f3'


In this test case, we get an extra space between the prefix and the original
subject.  It's because the original is *crooked*.  Note that a ``Subject``
starting with '\n ' is generated by some version of Eudora Japanese edition.

    >>> mlist.subject_prefix = '[XTest] '
    >>> msg = message_from_string("""\
    ... Subject:
    ...  Important message
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['subject']
    [XTest]  Important message

And again, with an RFC 2047 encoded header.

    >>> msg = message_from_string("""\
    ... Subject:
    ...  =?iso-2022-jp?b?GyRCJWEhPCVrJV4lcxsoQg==?=
    ...
    ... """)
    >>> process(mlist, msg, {})

..
 # XXX This one does not appear to work the same way as
 # test_subject_munging_prefix_crooked() in the old Python-based tests.  I need
 # to get Tokio to look at this.
 #    >>> print msg['subject']
 #    [XTest] =?iso-2022-jp?b?IBskQiVhITwlayVeJXMbKEI=?=
