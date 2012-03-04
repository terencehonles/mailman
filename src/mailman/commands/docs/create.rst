==========================
Command line list creation
==========================

A system administrator can create mailing lists by the command line.

    >>> class FakeArgs:
    ...     language = None
    ...     owners = []
    ...     quiet = False
    ...     domain = None
    ...     listname = None
    ...     notify = False

You cannot create a mailing list in an unknown domain.

    >>> from mailman.commands.cli_lists import Create
    >>> command = Create()

    >>> class FakeParser:
    ...     def error(self, message):
    ...         print message
    >>> command.parser = FakeParser()

    >>> FakeArgs.listname = ['test@example.xx']
    >>> command.process(FakeArgs)
    Undefined domain: example.xx

The ``-d`` or ``--domain`` option is used to tell Mailman to auto-register the
domain.  Both the mailing list and domain will be created.

    >>> FakeArgs.domain = True
    >>> command.process(FakeArgs)
    Created mailing list: test@example.xx

Now both the domain and the mailing list exist in the database.
::

    >>> from mailman.interfaces.listmanager import IListManager
    >>> from zope.component import getUtility
    >>> list_manager = getUtility(IListManager)
    >>> list_manager.get('test@example.xx')
    <mailing list "test@example.xx" at ...>

    >>> from mailman.interfaces.domain import IDomainManager
    >>> getUtility(IDomainManager).get('example.xx')
    <Domain example.xx, base_url: http://example.xx,
            contact_address: postmaster@example.xx>

You can also create mailing lists in existing domains without the
auto-creation flag.
::

    >>> FakeArgs.domain = False
    >>> FakeArgs.listname = ['test1@example.com']
    >>> command.process(FakeArgs)
    Created mailing list: test1@example.com

    >>> list_manager.get('test1@example.com')
    <mailing list "test1@example.com" at ...>

The command can also operate quietly.
::

    >>> FakeArgs.quiet = True
    >>> FakeArgs.listname = ['test2@example.com']
    >>> command.process(FakeArgs)

    >>> mlist = list_manager.get('test2@example.com')
    >>> mlist
    <mailing list "test2@example.com" at ...>


Setting the owner
=================

By default, no list owners are specified.

    >>> dump_list(mlist.owners.addresses)
    *Empty*

But you can specify an owner address on the command line when you create the
mailing list.
::

    >>> FakeArgs.quiet = False
    >>> FakeArgs.listname = ['test4@example.com']
    >>> FakeArgs.owners = ['foo@example.org']
    >>> command.process(FakeArgs)
    Created mailing list: test4@example.com

    >>> mlist = list_manager.get('test4@example.com')
    >>> dump_list(repr(address) for address in mlist.owners.addresses)
    <Address: foo@example.org [not verified] at ...>

You can even specify more than one address for the owners.
::

    >>> FakeArgs.owners = ['foo@example.net',
    ...                    'bar@example.net',
    ...                    'baz@example.net']
    >>> FakeArgs.listname = ['test5@example.com']
    >>> command.process(FakeArgs)
    Created mailing list: test5@example.com

    >>> mlist = list_manager.get('test5@example.com')
    >>> from operator import attrgetter
    >>> dump_list(repr(address) for address in mlist.owners.addresses)
    <Address: bar@example.net [not verified] at ...>
    <Address: baz@example.net [not verified] at ...>
    <Address: foo@example.net [not verified] at ...>


Setting the language
====================

You can set the default language for the new mailing list when you create it.
The language must be known to Mailman.
::

    >>> FakeArgs.listname = ['test3@example.com']
    >>> FakeArgs.language = 'ee'
    >>> command.process(FakeArgs)
    Invalid language code: ee

    >>> from mailman.interfaces.languages import ILanguageManager
    >>> getUtility(ILanguageManager).add('ee', 'iso-8859-1', 'Freedonian')
    <Language [ee] Freedonian>

    >>> FakeArgs.quiet = False
    >>> FakeArgs.listname = ['test3@example.com']
    >>> FakeArgs.language = 'fr'
    >>> command.process(FakeArgs)
    Created mailing list: test3@example.com

    >>> mlist = list_manager.get('test3@example.com')
    >>> print mlist.preferred_language
    <Language [fr] French>
    >>> FakeArgs.language = None


Notifications
=============

When told to, Mailman will notify the list owners of their new mailing list.

    >>> FakeArgs.listname = ['test6@example.com']
    >>> FakeArgs.notify = True
    >>> command.process(FakeArgs)
    Created mailing list: test6@example.com

The notification message is in the virgin queue.
::

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> for message in messages:
    ...     print message.msg.as_string()
    MIME-Version: 1.0
    ...
    Subject: Your new mailing list: test6@example.com
    From: noreply@example.com
    To: foo@example.net, bar@example.net, baz@example.net
    ...
    <BLANKLINE>
    The mailing list 'test6@example.com' has just been created for you.
    The following is some basic information about your mailing list.
    <BLANKLINE>
    You can configure your mailing list at the following web page:
    <BLANKLINE>
        http://lists.example.com/admin/test6@example.com
    <BLANKLINE>
    The web page for users of your mailing list is:
    <BLANKLINE>
        http://lists.example.com/listinfo/test6@example.com
    <BLANKLINE>
    There is also an email-based interface for users (not administrators)
    of your list; you can get info about using it by sending a message
    with just the word 'help' as subject or in the body, to:
    <BLANKLINE>
        test6-request@example.com
    <BLANKLINE>
    Please address all questions to noreply@example.com.
    <BLANKLINE>
