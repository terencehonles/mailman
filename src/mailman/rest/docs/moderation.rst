=======================
Held message moderation
=======================

Held messages can be moderated through the REST API.  A mailing list starts
out with no held messages.

    >>> ant = create_list('ant@example.com')
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held')
    http_etag: "..."
    start: 0
    total_size: 0

When a message gets held for moderator approval, it shows up in this list.
::

    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: ant@example.com
    ... Subject: Something
    ... Message-ID: <alpha>
    ...
    ... Something else.
    ... """)

    >>> from mailman.app.moderator import hold_message
    >>> request_id = hold_message(ant, msg, {'extra': 7}, 'Because')
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held')
    entry 0:
        data: {u'_mod_subject': u'Something',
               u'_mod_message_id': u'<alpha>',
               u'extra': 7,
               u'_mod_fqdn_listname': u'ant@example.com',
               u'_mod_hold_date': u'2005-08-01T07:49:23',
               u'_mod_reason': u'Because',
               u'_mod_sender': u'anne@example.com'}
        http_etag: "..."
        id: 1
        key: <alpha>
    http_etag: "..."
    start: 0
    total_size: 1

You can get an individual held message by providing the *request id* for that
message.  This will include the text of the message.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held/1')
    data: {u'_mod_subject': u'Something',
           u'_mod_message_id': u'<alpha>',
           u'extra': 7,
           u'_mod_fqdn_listname': u'ant@example.com',
           u'_mod_hold_date': u'2005-08-01T07:49:23',
           u'_mod_reason': u'Because',
           u'_mod_sender': u'anne@example.com'}
    http_etag: "..."
    id: 1
    key: <alpha>
    msg:
    From: anne@example.com
    To: ant@example.com
    Subject: Something
    Message-ID: <alpha>
    X-Message-ID-Hash: GCSMSG43GYWWVUMO6F7FBUSSPNXQCJ6M
    <BLANKLINE>
    Something else.
    <BLANKLINE>

Individual messages can be moderated through the API by POSTing back to the
held message's resource.   The POST data requires an action of one of the
following:

  * discard - throw the message away.
  * reject - bounces the message back to the original author.
  * defer - defer any action on the message (continue to hold it)
  * accept - accept the message for posting.

Let's see what happens when the above message is deferred.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held/1', {
    ...     'action': 'defer',
    ...     })
    content-length: 0
    date: ...
    server: ...
    status: 204

The message is still in the moderation queue.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held/1')
    data: {u'_mod_subject': u'Something',
           u'_mod_message_id': u'<alpha>',
           u'extra': 7,
           u'_mod_fqdn_listname': u'ant@example.com',
           u'_mod_hold_date': u'2005-08-01T07:49:23',
           u'_mod_reason': u'Because',
           u'_mod_sender': u'anne@example.com'}
    http_etag: "..."
    id: 1
    key: <alpha>
    msg: From: anne@example.com
    To: ant@example.com
    Subject: Something
    Message-ID: <alpha>
    X-Message-ID-Hash: GCSMSG43GYWWVUMO6F7FBUSSPNXQCJ6M
    <BLANKLINE>
    Something else.
    <BLANKLINE>

The held message can be discarded.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held/1', {
    ...     'action': 'discard',
    ...     })
    content-length: 0
    date: ...
    server: ...
    status: 204

After which, the message is gone from the moderation queue.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held/1')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found

- Hold another message
- Show accept
- Show reject? - probably not as we're just into testing app.moderator
