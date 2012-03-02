==================
Email command help
==================

You can get some help about the various email commands that are available by
sending the word `help` to a mailing list's -request address.

    >>> mlist = create_list('test@example.com')
    >>> from mailman.commands.eml_help import Help
    >>> help = Help()
    >>> print help.name
    help
    >>> print help.description
    Get help about available email commands.
    >>> print help.argument_description
    [command]

With no arguments, `help` provides a list of the available commands and a
short description of each of them.
::

    >>> from mailman.runners.command import Results
    >>> results = Results()

    >>> from mailman.email.message import Message
    >>> print help.process(mlist, Message(), {}, (), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    confirm     - Confirm a subscription request.
    echo        - Echo back your arguments.
    end         - Stop processing commands.
    help        - Get help about available email commands.
    join        - Join this mailing list.
    leave       - Leave this mailing list.
    stop        - An alias for 'end'.
    subscribe   - An alias for 'join'.
    unsubscribe - An alias for 'leave'.
    <BLANKLINE>

With an argument, you can get more detailed help about a specific command.

    >>> results = Results()
    >>> print help.process(mlist, Message(), {}, ('help',), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    help [command]
    Get help about available email commands.
    <BLANKLINE>
    
Some commands have even more detailed help.

    >>> results = Results()
    >>> print help.process(mlist, Message(), {}, ('join',), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    join [digest=<no|mime|plain>]
    Join this mailing list.
    <BLANKLINE>
    You will be asked to confirm your subscription request and you may be
    issued a provisional password.
    <BLANKLINE>
    By using the 'digest' option, you can specify whether you want digest
    delivery or not.  If not specified, the mailing list's default delivery
    mode will be used.
    <BLANKLINE>
