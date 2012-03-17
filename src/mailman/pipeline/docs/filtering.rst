=================
Content filtering
=================

Mailman can filter the content of messages posted to a mailing list by
stripping MIME subparts, and possibly reorganizing the MIME structure of a
message.

    >>> mlist = create_list('test@example.com')

Several mailing list options control content filtering.  First, the feature
must be enabled, then there are two options that control which MIME types get
filtered and which get passed.  Finally, there is an option to control whether
``text/html`` parts will get converted to plain text.  Let's set up some
defaults for these variables, then we'll explain them in more detail below.

    >>> mlist.filter_content = True
    >>> mlist.filter_types = []
    >>> mlist.pass_types = []
    >>> mlist.convert_html_to_plaintext = False


Filtering the outer content type
================================

A simple filtering setting will just search the content types of the messages
parts, discarding all parts with a matching MIME type.  If the message's outer
content type matches the filter, the entire message will be discarded.
::

    >>> from mailman.interfaces.mime import FilterAction

    >>> mlist.filter_types = ['image/jpeg']
    >>> mlist.filter_action = FilterAction.discard

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Content-Type: image/jpeg
    ... MIME-Version: 1.0
    ...
    ... xxxxx
    ... """)

    >>> process = config.handlers['mime-delete'].process
    >>> process(mlist, msg, {})
    Traceback (most recent call last):
    ...
    DiscardMessage: The message's content type was explicitly disallowed

However, if we turn off content filtering altogether, then the handler
short-circuits.

    >>> mlist.filter_content = False
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    From: aperson@example.com
    Content-Type: image/jpeg
    MIME-Version: 1.0
    <BLANKLINE>
    xxxxx
    >>> msgdata
    {}

Similarly, no content filtering is performed on digest messages, which are
crafted internally by Mailman.

    >>> mlist.filter_content = True
    >>> msgdata = {'isdigest': True}
    >>> process(mlist, msg, msgdata)
    >>> print msg.as_string()
    From: aperson@example.com
    Content-Type: image/jpeg
    MIME-Version: 1.0
    <BLANKLINE>
    xxxxx
    >>> msgdata
    {u'isdigest': True}


Simple multipart filtering
==========================

If one of the subparts in a multipart message matches the filter type, then
just that subpart will be stripped.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Content-Type: multipart/mixed; boundary=BOUNDARY
    ... MIME-Version: 1.0
    ...
    ... --BOUNDARY
    ... Content-Type: image/jpeg
    ... MIME-Version: 1.0
    ...
    ... xxx
    ...
    ... --BOUNDARY
    ... Content-Type: image/gif
    ... MIME-Version: 1.0
    ...
    ... yyy
    ... --BOUNDARY--
    ... """)

    >>> process(mlist, msg, {})
    >>> print msg.as_string()
    From: aperson@example.com
    Content-Type: multipart/mixed; boundary=BOUNDARY
    MIME-Version: 1.0
    X-Content-Filtered-By: Mailman/MimeDel ...
    <BLANKLINE>
    --BOUNDARY
    Content-Type: image/gif
    MIME-Version: 1.0
    <BLANKLINE>
    yyy
    --BOUNDARY--
    <BLANKLINE>


Collapsing multipart/alternative messages
=========================================

When content filtering encounters a ``multipart/alternative`` part, and the
results of filtering leave only one of the subparts, then the
``multipart/alternative`` may be collapsed.  For example, in the following
message, the outer content type is a ``multipart/mixed``.  Inside this part is
just a single subpart that has a content type of ``multipart/alternative``.
This inner multipart has two subparts, a jpeg and a gif.

Content filtering will remove the jpeg part, leaving the
``multipart/alternative`` with only a single gif subpart.  Because there's
only one subpart left, the MIME structure of the message will be reorganized,
removing the inner ``multipart/alternative`` so that the outer
``multipart/mixed`` has just a single gif subpart.

    >>> mlist.collapse_alternatives = True
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Content-Type: multipart/mixed; boundary=BOUNDARY
    ... MIME-Version: 1.0
    ...
    ... --BOUNDARY
    ... Content-Type: multipart/alternative; boundary=BOUND2
    ... MIME-Version: 1.0
    ...
    ... --BOUND2
    ... Content-Type: image/jpeg
    ... MIME-Version: 1.0
    ...
    ... xxx
    ...
    ... --BOUND2
    ... Content-Type: image/gif
    ... MIME-Version: 1.0
    ...
    ... yyy
    ... --BOUND2--
    ...
    ... --BOUNDARY--
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg.as_string()
    From: aperson@example.com
    Content-Type: multipart/mixed; boundary=BOUNDARY
    MIME-Version: 1.0
    X-Content-Filtered-By: Mailman/MimeDel ...
    <BLANKLINE>
    --BOUNDARY
    Content-Type: image/gif
    MIME-Version: 1.0
    <BLANKLINE>
    yyy
    --BOUNDARY--
    <BLANKLINE>

When the outer part is a ``multipart/alternative`` and filtering leaves this
outer part with just one subpart, the entire message is converted to the left
over part's content type.  In other words, the left over inner part is
promoted to being the outer part.
::

    >>> mlist.filter_types = ['image/jpeg', 'text/html']
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Content-Type: multipart/alternative; boundary=AAA
    ...
    ... --AAA
    ... Content-Type: text/html
    ...
    ... <b>This is some html</b>
    ... --AAA
    ... Content-Type: text/plain
    ...
    ... This is plain text
    ... --AAA--
    ... """)

    >>> process(mlist, msg, {})
    >>> print msg.as_string()
    From: aperson@example.com
    Content-Type: text/plain
    X-Content-Filtered-By: Mailman/MimeDel ...
    <BLANKLINE>
    This is plain text

Clean up.

    >>> mlist.filter_types = ['image/jpeg']


Conversion to plain text
========================

Many mailing lists prohibit HTML email, and in fact, such email can be a
phishing or spam vector.  However, many mail readers will send HTML email by
default because users think it looks pretty.  One approach to handling this
would be to filter out ``text/html`` parts and rely on
``multipart/alternative`` collapsing to leave just a plain text part.  This
works because many mail readers that send HTML email actually send a plain
text part in the second subpart of such ``multipart/alternatives``.

While this is a good suggestion for plain text-only mailing lists, often a
mail reader will send only a ``text/html`` part with no plain text
alternative.  in this case, the site administer can enable ``text/html`` to
``text/plain`` conversion by defining a conversion command.  A list
administrator still needs to enable such conversion for their list though.

    >>> mlist.convert_html_to_plaintext = True

By default, Mailman sends the message through lynx, but since this program is
not guaranteed to exist, we'll craft a simple, but stupid script to simulate
the conversion process.  The script expects a single argument, which is the
name of the file containing the message payload to filter.

    >>> import os, sys
    >>> script_path = os.path.join(config.DATA_DIR, 'filter.py')
    >>> fp = open(script_path, 'w')
    >>> try:
    ...     print >> fp, """\
    ... import sys
    ... print 'Converted text/html to text/plain'
    ... print 'Filename:', sys.argv[1]
    ... """
    ... finally:
    ...     fp.close()
    >>> config.HTML_TO_PLAIN_TEXT_COMMAND = '%s %s %%(filename)s' % (
    ...     sys.executable, script_path)
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Content-Type: text/html
    ... MIME-Version: 1.0
    ...
    ... <html><head></head>
    ... <body></body></html>
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg.as_string()
    From: aperson@example.com
    MIME-Version: 1.0
    Content-Type: text/plain
    X-Content-Filtered-By: Mailman/MimeDel ...
    <BLANKLINE>
    Converted text/html to text/plain
    Filename: ...
    <BLANKLINE>


Discarding empty parts
======================

Similarly, if after filtering a multipart section ends up empty, then the
entire multipart is discarded.  For example, here's a message where an inner
``multipart/mixed`` contains two jpeg subparts.  Both jpegs are filtered out,
so the entire inner ``multipart/mixed`` is discarded.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Content-Type: multipart/mixed; boundary=AAA
    ...
    ... --AAA
    ... Content-Type: multipart/mixed; boundary=BBB
    ...
    ... --BBB
    ... Content-Type: image/jpeg
    ...
    ... xxx
    ... --BBB
    ... Content-Type: image/jpeg
    ...
    ... yyy
    ... --BBB---
    ... --AAA
    ... Content-Type: multipart/alternative; boundary=CCC
    ...
    ... --CCC
    ... Content-Type: text/html
    ...
    ... <h2>This is a header</h2>
    ...
    ... --CCC
    ... Content-Type: text/plain
    ...
    ... A different message
    ... --CCC--
    ... --AAA
    ... Content-Type: image/gif
    ...
    ... zzz
    ... --AAA
    ... Content-Type: image/gif
    ...
    ... aaa
    ... --AAA--
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg.as_string()
    From: aperson@example.com
    Content-Type: multipart/mixed; boundary=AAA
    X-Content-Filtered-By: Mailman/MimeDel ...
    <BLANKLINE>
    --AAA
    MIME-Version: 1.0
    Content-Type: text/plain
    <BLANKLINE>
    Converted text/html to text/plain
    Filename: ...
    <BLANKLINE>
    --AAA
    Content-Type: image/gif
    <BLANKLINE>
    zzz
    --AAA
    Content-Type: image/gif
    <BLANKLINE>
    aaa
    --AAA--
    <BLANKLINE>


Passing MIME types
==================

XXX Describe the pass_mime_types setting and how it interacts with
``filter_mime_types``.
