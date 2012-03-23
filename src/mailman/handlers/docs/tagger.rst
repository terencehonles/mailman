==============
Message tagger
==============

Mailman has a topics system which works like this: a mailing list
administrator sets up one or more topics, which is essentially a named regular
expression.  The topic name can be any arbitrary string, and the name serves
double duty as the *topic tag*.  Each message that flows the mailing list has
its ``Subject:`` and ``Keywords:`` headers compared against these regular
expressions.  The message then gets tagged with the topic names of each hit.

    >>> mlist = create_list('_xtest@example.com')

Topics must be enabled for Mailman to do any topic matching, even if topics
are defined.
::

    >>> mlist.topics = [('bar fight', '.*bar.*', 'catch any bars', False)]
    >>> mlist.topics_enabled = False
    >>> mlist.topics_bodylines_limit = 0

    >>> msg = message_from_string("""\
    ... Subject: foobar
    ... Keywords: barbaz
    ...
    ... """)
    >>> msgdata = {}

    >>> from mailman.handlers.tagger import process
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    Subject: foobar
    Keywords: barbaz
    <BLANKLINE>
    <BLANKLINE>
    >>> msgdata
    {}

However, once topics are enabled, message will be tagged.  There are two
artifacts of tagging; an ``X-Topics:`` header is added with the topic name,
and the message metadata gets a key with a list of matching topic names.

    >>> mlist.topics_enabled = True
    >>> msg = message_from_string("""\
    ... Subject: foobar
    ... Keywords: barbaz
    ...
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    Subject: foobar
    Keywords: barbaz
    X-Topics: bar fight
    <BLANKLINE>
    <BLANKLINE>
    >>> msgdata['topichits']
    [u'bar fight']


Scanning body lines
===================

The tagger can also look at a certain number of body lines, but only for
``Subject:`` and ``Keyword:`` header-like lines.  When set to zero, no body
lines are scanned.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: nothing
    ... Keywords: at all
    ...
    ... X-Ignore: something else
    ... Subject: foobar
    ... Keywords: barbaz
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    From: aperson@example.com
    Subject: nothing
    Keywords: at all
    <BLANKLINE>
    X-Ignore: something else
    Subject: foobar
    Keywords: barbaz
    <BLANKLINE>
    >>> msgdata
    {}

But let the tagger scan a few body lines and the matching headers will be
found.

    >>> mlist.topics_bodylines_limit = 5
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: nothing
    ... Keywords: at all
    ...
    ... X-Ignore: something else
    ... Subject: foobar
    ... Keywords: barbaz
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    From: aperson@example.com
    Subject: nothing
    Keywords: at all
    X-Topics: bar fight
    <BLANKLINE>
    X-Ignore: something else
    Subject: foobar
    Keywords: barbaz
    <BLANKLINE>
    >>> msgdata['topichits']
    [u'bar fight']

However, scanning stops at the first body line that doesn't look like a
header.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: nothing
    ... Keywords: at all
    ...
    ... This is not a header
    ... Subject: foobar
    ... Keywords: barbaz
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    From: aperson@example.com
    Subject: nothing
    Keywords: at all
    <BLANKLINE>
    This is not a header
    Subject: foobar
    Keywords: barbaz
    >>> msgdata
    {}

When set to a negative number, all body lines will be scanned.

    >>> mlist.topics_bodylines_limit = -1
    >>> lots_of_headers = '\n'.join(['X-Ignore: zip'] * 100)
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: nothing
    ... Keywords: at all
    ...
    ... %s
    ... Subject: foobar
    ... Keywords: barbaz
    ... """ % lots_of_headers)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> # Rather than print out 100 X-Ignore: headers, let's just prove that
    >>> # the X-Topics: header exists, meaning that the tagger did its job.
    >>> print msg['x-topics']
    bar fight
    >>> msgdata['topichits']
    [u'bar fight']


Scanning sub-parts
==================

The tagger will also scan the body lines of text subparts in a multipart
message, using the same rules as if all those body lines lived in a single
text payload.

    >>> msg = message_from_string("""\
    ... Subject: Was
    ... Keywords: Raw
    ... Content-Type: multipart/alternative; boundary="BOUNDARY"
    ... 
    ... --BOUNDARY
    ... From: sabo
    ... To: obas
    ... 
    ... Subject: farbaw
    ... Keywords: barbaz
    ... 
    ... --BOUNDARY--
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    Subject: Was
    Keywords: Raw
    Content-Type: multipart/alternative; boundary="BOUNDARY"
    X-Topics: bar fight
    <BLANKLINE>
    --BOUNDARY
    From: sabo
    To: obas
    <BLANKLINE>
    Subject: farbaw
    Keywords: barbaz
    <BLANKLINE>
    --BOUNDARY--
    <BLANKLINE>
    >>> msgdata['topichits']
    [u'bar fight']

But the tagger will not descend into non-text parts.

    >>> msg = message_from_string("""\
    ... Subject: Was
    ... Keywords: Raw
    ... Content-Type: multipart/alternative; boundary=BOUNDARY
    ... 
    ... --BOUNDARY
    ... From: sabo
    ... To: obas
    ... Content-Type: message/rfc822
    ... 
    ... Subject: farbaw
    ... Keywords: barbaz
    ... 
    ... --BOUNDARY
    ... From: sabo
    ... To: obas
    ... Content-Type: message/rfc822
    ... 
    ... Subject: farbaw
    ... Keywords: barbaz
    ... 
    ... --BOUNDARY--
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msg['x-topics']
    None
    >>> msgdata
    {}
