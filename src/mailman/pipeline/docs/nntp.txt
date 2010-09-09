============
NNTP Gateway
============

Mailman has an NNTP gateway, whereby messages posted to the mailing list can
be forwarded onto an NNTP newsgroup.  Typically this means Usenet, but since
NNTP is to Usenet as IP is to the web, it's more general than that.

    >>> mlist = create_list('_xtest@example.com')

Gatewaying from the mailing list to the newsgroup happens through a separate
``nntp`` queue and happen immediately when the message is posted through to
the list.  Note that gatewaying from the newsgroup to the list happens via a
cronjob (currently not shown).

There are several situations which prevent a message from being gatewayed to
the newsgroup.  The feature could be disabled, as is the default.
::

    >>> mlist.gateway_to_news = False
    >>> msg = message_from_string("""\
    ... Subject: An important message
    ...
    ... Something of great import.
    ... """)

    >>> handler = config.handlers['to-usenet']
    >>> handler.process(mlist, msg, {})

    >>> switchboard = config.switchboards['news']
    >>> switchboard.files
    []

Even if enabled, messages that came from the newsgroup are never gated back to
the newsgroup.

    >>> mlist.gateway_to_news = True
    >>> handler.process(mlist, msg, {'fromusenet': True})
    >>> switchboard.files
    []

Neither are digests ever gated to the newsgroup.

    >>> handler.process(mlist, msg, {'isdigest': True})
    >>> switchboard.files
    []

However, other posted messages get gated to the newsgroup via the nntp queue.
The list owner can set the linked newsgroup and the nntp host that its
messages are gated to.

    >>> mlist.linked_newsgroup = 'comp.lang.thing'
    >>> mlist.nntp_host = 'news.example.com'
    >>> handler.process(mlist, msg, {})
    >>> len(switchboard.files)
    1
    >>> filebase = switchboard.files[0]
    >>> msg, msgdata = switchboard.dequeue(filebase)
    >>> switchboard.finish(filebase)
    >>> print msg.as_string()
    Subject: An important message
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>
    >>> dump_msgdata(msgdata)
    _parsemsg: False
    listname : _xtest@example.com
    version  : 3
