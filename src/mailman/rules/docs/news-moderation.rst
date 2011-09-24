====================
Newsgroup moderation
====================

The ``news-moderation`` rule matches all messages posted to mailing lists that
gateway to a moderated newsgroup.  The reason for this is that such messages
must get forwarded on to the newsgroup moderator.  From there it will get
posted to the newsgroup, and from there, gated to the mailing list.  It's a
circuitous route, but it works nonetheless by holding all messages posted
directly to the mailing list.

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['news-moderation']
    >>> print rule.name
    news-moderation

Set the list configuration variable to enable newsgroup moderation.

    >>> from mailman.interfaces.nntp import NewsModeration
    >>> mlist.news_moderation = NewsModeration.moderated

And now all messages will match the rule.

    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... Subject: An announcement
    ...
    ... Great things are happening.
    ... """)
    >>> rule.check(mlist, msg, {})
    True

When moderation is turned off, the rule does not match.

    >>> mlist.news_moderation = NewsModeration.none
    >>> rule.check(mlist, msg, {})
    False
