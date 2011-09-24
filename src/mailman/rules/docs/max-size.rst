============
Message size
============

The ``message-size`` rule matches when the posted message is bigger than a
specified maximum.  Generally this is used to prevent huge attachments from
getting posted to the list.  This value is calculated in terms of KB (1024
bytes).

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['max-size']
    >>> print rule.name
    max-size

For example, setting the maximum message size to 1 means that any message
bigger than that will match the rule.

    >>> mlist.max_message_size = 1 # 1024 bytes
    >>> one_line = 'x' * 79
    >>> big_body = '\n'.join([one_line] * 15)
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: _xtest@example.com
    ...
    ... """ + big_body)
    >>> rule.check(mlist, msg, {})
    True

Setting the maximum message size to zero means no size check is performed.

    >>> mlist.max_message_size = 0
    >>> rule.check(mlist, msg, {})
    False

Of course, if the maximum size is larger than the message's size, then it's
still okay.

    >>> mlist.max_message_size = msg.original_size/1024.0 + 1
    >>> rule.check(mlist, msg, {})
    False
