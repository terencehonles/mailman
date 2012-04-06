===============
Header matching
===============

Mailman can do pattern based header matching during its normal rule
processing.  There is a set of site-wide default header matches specified in
the configuration file under the `[antispam]` section.

    >>> mlist = create_list('test@example.com')

In this section, the variable `header_checks` contains a list of the headers
to check, and the patterns to check them against.  By default, this list is
empty.

It is also possible to programmatically extend these header checks.  Here,
we'll extend the checks with a pattern that matches 4 or more stars.

    >>> chain = config.chains['header-match']
    >>> chain.extend('x-spam-score', '[*]{4,}')

First, if the message has no ``X-Spam-Score:`` header, the message passes
through the chain with no matches.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: Not spam
    ... Message-ID: <ant>
    ...
    ... This is a message.
    ... """)

.. Function to help with printing rule hits and misses.
    >>> def hits_and_misses(msgdata):
    ...     hits = msgdata.get('rule_hits', [])
    ...     if len(hits) == 0:
    ...         print 'No rules hit'
    ...     else:
    ...         print 'Rule hits:'
    ...         for rule_name in hits:
    ...             rule = config.rules[rule_name]
    ...             print '    {0}: {1}'.format(rule.header, rule.pattern)
    ...     misses = msgdata.get('rule_misses', [])
    ...     if len(misses) == 0:
    ...         print 'No rules missed'
    ...     else:
    ...         print 'Rule misses:'
    ...         for rule_name in misses:
    ...             rule = config.rules[rule_name]
    ...             print '    {0}: {1}'.format(rule.header, rule.pattern)

By looking at the message metadata after chain processing, we can see that
none of the rules matched.

    >>> from mailman.core.chains import process
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata, 'header-match')
    >>> hits_and_misses(msgdata)
    No rules hit
    Rule misses:
        x-spam-score: [*]{4,}

The header may exist but does not match the pattern.

    >>> msg['X-Spam-Score'] = '***'
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata, 'header-match')
    >>> hits_and_misses(msgdata)
    No rules hit
    Rule misses:
        x-spam-score: [*]{4,}

The header may exist and match the pattern.  By default, when the header
matches, it gets held for moderator approval.
::

    >>> from mailman.testing.helpers import event_subscribers
    >>> def handler(event):
    ...     print event.__class__.__name__, \
    ...           event.chain.name, event.msg['message-id']

    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '*****'
    >>> msgdata = {}
    >>> with event_subscribers(handler):
    ...     process(mlist, msg, msgdata, 'header-match')
    HoldNotification hold <ant>

    >>> hits_and_misses(msgdata)
    Rule hits:
        x-spam-score: [*]{4,}
    No rules missed

The configuration file can also specify a different final disposition for
messages that match their header checks.  For example, we may just want to
discard such messages.

    >>> from mailman.testing.helpers import configuration
    >>> msgdata = {}
    >>> with event_subscribers(handler):
    ...     with configuration('antispam', jump_chain='discard'):
    ...         process(mlist, msg, msgdata, 'header-match')
    DiscardNotification discard <ant>

These programmatically added headers can be removed by flushing the chain.
Now, nothing with match this message.

    >>> chain.flush()
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata, 'header-match')
    >>> hits_and_misses(msgdata)
    No rules hit
    No rules missed


List-specific header matching
=============================

Each mailing list can also be configured with a set of header matching regular
expression rules.  These are used to impose list-specific header filtering
with the same semantics as the global `[antispam]` section.

The list administrator wants to match not on four stars, but on three plus
signs, but only for the current mailing list.

    >>> mlist.header_matches = [('x-spam-score', '[+]{3,}')]

A message with a spam score of two pluses does not match.

    >>> msgdata = {}
    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '++'
    >>> process(mlist, msg, msgdata, 'header-match')
    >>> hits_and_misses(msgdata)
    No rules hit
    Rule misses:
        x-spam-score: [+]{3,}

But a message with a spam score of three pluses does match.  Because a message
with the previous Message-Id is already in the moderation queue, we need to
give this message a new Message-Id.

    >>> msgdata = {}
    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '+++'
    >>> del msg['message-id']
    >>> msg['Message-Id'] = '<bee>'
    >>> process(mlist, msg, msgdata, 'header-match')
    >>> hits_and_misses(msgdata)
    Rule hits:
        x-spam-score: [+]{3,}
    No rules missed

As does a message with a spam score of four pluses.

    >>> msgdata = {}
    >>> del msg['x-spam-score']
    >>> msg['X-Spam-Score'] = '++++'
    >>> del msg['message-id']
    >>> msg['Message-Id'] = '<cat>'
    >>> process(mlist, msg, msgdata, 'header-match')
    >>> hits_and_misses(msgdata)
    Rule hits:
        x-spam-score: [+]{3,}
    No rules missed
