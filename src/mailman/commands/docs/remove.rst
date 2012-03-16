=========================
Command line list removal
=========================

A system administrator can remove mailing lists by the command line.
::

    >>> create_list('test@example.com')
    <mailing list "test@example.com" at ...>

    >>> from mailman.interfaces.listmanager import IListManager
    >>> from zope.component import getUtility
    >>> list_manager = getUtility(IListManager)
    >>> list_manager.get('test@example.com')
    <mailing list "test@example.com" at ...>

    >>> class FakeArgs:
    ...     quiet = False
    ...     archives = False
    ...     listname = ['test@example.com']
    >>> args = FakeArgs()

    >>> from mailman.commands.cli_lists import Remove
    >>> command = Remove()
    >>> command.process(args)
    Removed list: test@example.com

    >>> print list_manager.get('test@example.com')
    None

You can also remove lists quietly.
::

    >>> create_list('test@example.com')
    <mailing list "test@example.com" at ...>

    >>> args.quiet = True
    >>> command.process(args)

    >>> print list_manager.get('test@example.com')
    None
