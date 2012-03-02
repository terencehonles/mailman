==================
The 'echo' command
==================

The mail command 'echo' simply replies with the original command and arguments
to the sender.

    >>> command = config.commands['echo']
    >>> print command.name
    echo
    >>> print command.argument_description
    [args]
    >>> print command.description
    Echo back your arguments.

The original message is ignored, but the results receive the echoed command.
::

    >>> mlist = create_list('test@example.com')

    >>> from mailman.runners.command import Results
    >>> results = Results()

    >>> from mailman.email.message import Message
    >>> print command.process(mlist, Message(), {}, ('foo', 'bar'), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    echo foo bar
    <BLANKLINE>
