===============
Header matching
===============

Mailman can do pattern based header matching during its normal rule
processing.  There is a set of site-wide default header matches specified in
the configuration file under the ``[spam.headers]`` section.

    >>> mlist = create_list('test@example.com')

Because the default ``[spam.headers]`` section is empty, we'll just extend the
current header matching chain with a pattern that matches 4 or more stars,
discarding the message if it hits.

    >>> chain = config.chains['header-match']
    >>> chain.extend('x-spam-score', '[*]{4,}', 'discard')

First, if the message has no ``X-Spam-Score:`` header, the message passes
through the chain untouched (i.e. no disposition).
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: Not spam
    ... Message-ID: <one>
    ...
    ... This is a message.
    ... """)

    >>> from mailman.core.chains import process

Pass through is seen as nothing being in the log file after processing.
::

    # XXX This checks the vette log file because there is no other evidence
    # that this chain has done anything.
    >>> import os
    >>> fp = open(os.path.join(config.LOG_DIR, 'vette'))
    >>> fp.seek(0, 2)
    >>> file_pos = fp.tell()
    >>> process(mlist, msg, {}, 'header-match')
    >>> fp.seek(file_pos)
    >>> print 'LOG:', fp.read()
    LOG:
    <BLANKLINE>

Now, if the header exists but does not match, then it also passes through
untouched.

    >>> msg['X-Spam-Score'] = '***'
    >>> del msg['subject']
    >>> msg['Subject'] = 'This is almost spam'
    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<two>'
    >>> file_pos = fp.tell()
    >>> process(mlist, msg, {}, 'header-match')
    >>> fp.seek(file_pos)
    >>> print 'LOG:', fp.read()
    LOG:
    <BLANKLINE>

But now if the header matches, then the message gets discarded.

    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '****'
    >>> del msg['subject']
    >>> msg['Subject'] = 'This is spam, but barely'
    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<three>'
    >>> file_pos = fp.tell()
    >>> process(mlist, msg, {}, 'header-match')
    >>> fp.seek(file_pos)
    >>> print 'LOG:', fp.read()
    LOG: ... DISCARD: <three>
    <BLANKLINE>

For kicks, let's show a message that's really spammy.

    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '**********'
    >>> del msg['subject']
    >>> msg['Subject'] = 'This is really spammy'
    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<four>'
    >>> file_pos = fp.tell()
    >>> process(mlist, msg, {}, 'header-match')
    >>> fp.seek(file_pos)
    >>> print 'LOG:', fp.read()
    LOG: ... DISCARD: <four>
    <BLANKLINE>

Flush out the extended header matching rules.

    >>> chain.flush()


List-specific header matching
=============================

Each mailing list can also be configured with a set of header matching regular
expression rules.  These are used to impose list-specific header filtering
with the same semantics as the global ``[spam.headers]`` section.

The list administrator wants to match not on four stars, but on three plus
signs, but only for the current mailing list.

    >>> mlist.header_matches = [('x-spam-score', '[+]{3,}', 'discard')]

A message with a spam score of two pluses does not match.

    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '++'
    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<five>'
    >>> file_pos = fp.tell()
    >>> process(mlist, msg, {}, 'header-match')
    >>> fp.seek(file_pos)
    >>> print 'LOG:', fp.read()
    LOG:

A message with a spam score of three pluses does match.

    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '+++'
    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<six>'
    >>> file_pos = fp.tell()
    >>> process(mlist, msg, {}, 'header-match')
    >>> fp.seek(file_pos)
    >>> print 'LOG:', fp.read()
    LOG: ... DISCARD: <six>
    <BLANKLINE>

As does a message with a spam score of four pluses.

    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '+++'
    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<seven>'
    >>> file_pos = fp.tell()
    >>> process(mlist, msg, {}, 'header-match')
    >>> fp.seek(file_pos)
    >>> print 'LOG:', fp.read()
    LOG: ... DISCARD: <seven>
    <BLANKLINE>
