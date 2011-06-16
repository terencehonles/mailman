==========================
Mailing list configuration
==========================

Mailing lists can be configured via the REST API.

    >>> mlist = create_list('test-one@example.com')
    >>> transaction.commit()


Reading a configuration
=======================

All readable attributes for a list are available on a sub-resource.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config')
    acceptable_aliases: []
    admin_immed_notify: True
    admin_notify_mchanges: False
    administrivia: True
    advertised: True
    anonymous_list: False
    autorespond_owner: none
    autorespond_postings: none
    autorespond_requests: none
    autoresponse_grace_period: 90d
    autoresponse_owner_text:
    autoresponse_postings_text:
    autoresponse_request_text:
    bounces_address: test-one-bounces@example.com
    collapse_alternatives: True
    convert_html_to_plaintext: False
    created_at: 20...T...
    default_member_action: defer
    default_nonmember_action: hold
    description:
    digest_last_sent_at: None
    digest_size_threshold: 30.0
    filter_content: False
    fqdn_listname: test-one@example.com
    generic_nonmember_action: 1
    http_etag: "..."
    include_list_post_header: True
    include_rfc2369_headers: True
    join_address: test-one-join@example.com
    last_post_at: None
    leave_address: test-one-leave@example.com
    list_id: test-one.example.com
    list_name: test-one
    mail_host: example.com
    next_digest_number: 1
    no_reply_address: noreply@example.com
    owner_address: test-one-owner@example.com
    pipeline: built-in
    post_id: 1
    posting_address: test-one@example.com
    real_name: Test-one
    reply_goes_to_list: no_munging
    request_address: test-one-request@example.com
    scheme: http
    send_welcome_msg: True
    volume: 1
    web_host: lists.example.com
    welcome_msg:


Changing the full configuration
===============================

Not all of the readable attributes can be set through the web interface.  The
ones that can, can either be set via ``PUT`` or ``PATCH``.  ``PUT`` changes
all the writable attributes in one request.

    >>> from mailman.interfaces.action import Action
    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config',
    ...           dict(
    ...             acceptable_aliases=['one@example.com', 'two@example.com'],
    ...             admin_immed_notify=False,
    ...             admin_notify_mchanges=True,
    ...             administrivia=False,
    ...             advertised=False,
    ...             anonymous_list=True,
    ...             autorespond_owner='respond_and_discard',
    ...             autorespond_postings='respond_and_continue',
    ...             autorespond_requests='respond_and_discard',
    ...             autoresponse_grace_period='45d',
    ...             autoresponse_owner_text='the owner',
    ...             autoresponse_postings_text='the mailing list',
    ...             autoresponse_request_text='the robot',
    ...             real_name='Fnords',
    ...             description='This is my mailing list',
    ...             include_rfc2369_headers=False,
    ...             include_list_post_header=False,
    ...             digest_size_threshold=10.5,
    ...             pipeline='virgin',
    ...             filter_content=True,
    ...             convert_html_to_plaintext=True,
    ...             collapse_alternatives=False,
    ...             reply_goes_to_list='point_to_list',
    ...             send_welcome_msg=False,
    ...             welcome_msg='Welcome!',
    ...             default_member_action='hold',
    ...             default_nonmember_action='discard',
    ...             generic_nonmember_action=2,
    ...             ),
    ...           'PUT')
    content-length: 0
    date: ...
    server: WSGIServer/...
    status: 204

These values are changed permanently.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config')
    acceptable_aliases: [u'one@example.com', u'two@example.com']
    admin_immed_notify: False
    admin_notify_mchanges: True
    administrivia: False
    advertised: False
    anonymous_list: True
    autorespond_owner: respond_and_discard
    autorespond_postings: respond_and_continue
    autorespond_requests: respond_and_discard
    autoresponse_grace_period: 45d
    autoresponse_owner_text: the owner
    autoresponse_postings_text: the mailing list
    autoresponse_request_text: the robot
    ...
    collapse_alternatives: False
    convert_html_to_plaintext: True
    ...
    default_member_action: hold
    default_nonmember_action: discard
    description: This is my mailing list
    ...
    digest_size_threshold: 10.5
    filter_content: True
    ...
    include_list_post_header: False
    include_rfc2369_headers: False
    ...
    pipeline: virgin
    ...
    real_name: Fnords
    reply_goes_to_list: point_to_list
    ...
    send_welcome_msg: False
    ...
    welcome_msg: Welcome!

If you use ``PUT`` to change a list's configuration, all writable attributes
must be included.  It is an error to leave one or more out...

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config',
    ...           dict(
    ...             #acceptable_aliases=['one', 'two'],
    ...             admin_immed_notify=False,
    ...             admin_notify_mchanges=True,
    ...             administrivia=False,
    ...             advertised=False,
    ...             anonymous_list=True,
    ...             autorespond_owner='respond_and_discard',
    ...             autorespond_postings='respond_and_continue',
    ...             autorespond_requests='respond_and_discard',
    ...             autoresponse_grace_period='45d',
    ...             autoresponse_owner_text='the owner',
    ...             autoresponse_postings_text='the mailing list',
    ...             autoresponse_request_text='the robot',
    ...             real_name='Fnords',
    ...             description='This is my mailing list',
    ...             include_rfc2369_headers=False,
    ...             include_list_post_header=False,
    ...             digest_size_threshold=10.5,
    ...             pipeline='virgin',
    ...             filter_content=True,
    ...             convert_html_to_plaintext=True,
    ...             collapse_alternatives=False,
    ...             reply_goes_to_list='point_to_list',
    ...             send_welcome_msg=True,
    ...             welcome_msg='welcome message',
    ...             default_member_action='accept',
    ...             default_nonmember_action='accept',
    ...             generic_nonmember_action=2,
    ...             ),
    ...           'PUT')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 400: Missing parameters: acceptable_aliases

...or to add an unknown one.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config',
    ...           dict(
    ...             a_mailing_list_attribute=False,
    ...             acceptable_aliases=['one', 'two'],
    ...             admin_immed_notify=False,
    ...             admin_notify_mchanges=True,
    ...             administrivia=False,
    ...             advertised=False,
    ...             anonymous_list=True,
    ...             autorespond_owner='respond_and_discard',
    ...             autorespond_postings='respond_and_continue',
    ...             autorespond_requests='respond_and_discard',
    ...             autoresponse_grace_period='45d',
    ...             autoresponse_owner_text='the owner',
    ...             autoresponse_postings_text='the mailing list',
    ...             autoresponse_request_text='the robot',
    ...             real_name='Fnords',
    ...             description='This is my mailing list',
    ...             include_rfc2369_headers=False,
    ...             include_list_post_header=False,
    ...             digest_size_threshold=10.5,
    ...             pipeline='virgin',
    ...             filter_content=True,
    ...             convert_html_to_plaintext=True,
    ...             collapse_alternatives=False,
    ...             ),
    ...           'PUT')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 400: Unexpected parameters: a_mailing_list_attribute

It is also an error to spell an attribute value incorrectly...

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config',
    ...           dict(
    ...             admin_immed_notify='Nope',
    ...             acceptable_aliases=['one', 'two'],
    ...             admin_notify_mchanges=True,
    ...             administrivia=False,
    ...             advertised=False,
    ...             anonymous_list=True,
    ...             autorespond_owner='respond_and_discard',
    ...             autorespond_postings='respond_and_continue',
    ...             autorespond_requests='respond_and_discard',
    ...             autoresponse_grace_period='45d',
    ...             autoresponse_owner_text='the owner',
    ...             autoresponse_postings_text='the mailing list',
    ...             autoresponse_request_text='the robot',
    ...             real_name='Fnords',
    ...             description='This is my mailing list',
    ...             include_rfc2369_headers=False,
    ...             include_list_post_header=False,
    ...             digest_size_threshold=10.5,
    ...             pipeline='virgin',
    ...             filter_content=True,
    ...             convert_html_to_plaintext=True,
    ...             collapse_alternatives=False,
    ...             ),
    ...           'PUT')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 400: Cannot convert parameters: admin_immed_notify

...or to name a pipeline that doesn't exist...

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config',
    ...           dict(
    ...             acceptable_aliases=['one', 'two'],
    ...             admin_immed_notify=False,
    ...             admin_notify_mchanges=True,
    ...             advertised=False,
    ...             anonymous_list=True,
    ...             autorespond_owner='respond_and_discard',
    ...             autorespond_postings='respond_and_continue',
    ...             autorespond_requests='respond_and_discard',
    ...             autoresponse_grace_period='45d',
    ...             autoresponse_owner_text='the owner',
    ...             autoresponse_postings_text='the mailing list',
    ...             autoresponse_request_text='the robot',
    ...             real_name='Fnords',
    ...             description='This is my mailing list',
    ...             include_rfc2369_headers=False,
    ...             include_list_post_header=False,
    ...             digest_size_threshold=10.5,
    ...             pipeline='dummy',
    ...             filter_content=True,
    ...             convert_html_to_plaintext=True,
    ...             collapse_alternatives=False,
    ...             ),
    ...           'PUT')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 400: Cannot convert parameters: pipeline

...or to name an invalid auto-response enumeration value.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config',
    ...           dict(
    ...             acceptable_aliases=['one', 'two'],
    ...             admin_immed_notify=False,
    ...             admin_notify_mchanges=True,
    ...             advertised=False,
    ...             anonymous_list=True,
    ...             autorespond_owner='do_not_respond',
    ...             autorespond_postings='respond_and_continue',
    ...             autorespond_requests='respond_and_discard',
    ...             autoresponse_grace_period='45d',
    ...             autoresponse_owner_text='the owner',
    ...             autoresponse_postings_text='the mailing list',
    ...             autoresponse_request_text='the robot',
    ...             real_name='Fnords',
    ...             description='This is my mailing list',
    ...             include_rfc2369_headers=False,
    ...             include_list_post_header=False,
    ...             digest_size_threshold=10.5,
    ...             pipeline='virgin',
    ...             filter_content=True,
    ...             convert_html_to_plaintext=True,
    ...             collapse_alternatives=False,
    ...             ),
    ...           'PUT')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 400: Cannot convert parameters: autorespond_owner


Changing a partial configuration
================================

Using ``PATCH``, you can change just one attribute.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config',
    ...           dict(real_name='My List'),
    ...           'PATCH')
    content-length: 0
    date: ...
    server: ...
    status: 204

These values are changed permanently.

    >>> print mlist.real_name
    My List


Sub-resources
=============

Many of the mailing list configuration variables are actually available as
sub-resources on the mailing list.  This is because they are collections,
sequences, and other complex configuration types.  Their values can be
retrieved and set through the sub-resource.


Acceptable aliases
------------------

These are recipient aliases that can be used in the ``To:`` and ``CC:``
headers instead of the posting address.  They are often used in forwarded
emails.  By default, a mailing list has no acceptable aliases.

    >>> from mailman.interfaces.mailinglist import IAcceptableAliasSet
    >>> IAcceptableAliasSet(mlist).clear()
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config/acceptable_aliases')
    acceptable_aliases: []
    http_etag: "..."

We can add a few by ``PUT``-ing them on the sub-resource.  The keys in the
dictionary are ignored.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'test-one@example.com/config/acceptable_aliases',
    ...           dict(acceptable_aliases=['foo@example.com',
    ...                                    'bar@example.net']),
    ...           'PUT')
    content-length: 0
    date: ...
    server: WSGIServer/...
    status: 204

Aliases are returned as a list on the ``aliases`` key.

    >>> response = call_http(
    ...     'http://localhost:9001/3.0/lists/'
    ...     'test-one@example.com/config/acceptable_aliases')
    >>> for alias in response['acceptable_aliases']:
    ...     print alias
    bar@example.net
    foo@example.com

The mailing list has its aliases set.

    >>> from mailman.interfaces.mailinglist import IAcceptableAliasSet
    >>> aliases = IAcceptableAliasSet(mlist)
    >>> for alias in sorted(aliases.aliases):
    ...     print alias
    bar@example.net
    foo@example.com
