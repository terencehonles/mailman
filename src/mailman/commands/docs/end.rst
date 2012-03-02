=================
The 'end' command
=================

The mail command processor recognized an 'end' command which tells it to stop
processing email messages.

    >>> command = config.commands['end']
    >>> print command.name
    end
    >>> print command.description
    Stop processing commands.

The 'end' command takes no arguments.

    >>> command.argument_description
    ''

The command itself is fairly simple; it just stops command processing, and the
message isn't even looked at.

    >>> mlist = create_list('test@example.com')
    >>> from mailman.email.message import Message
    >>> print command.process(mlist, Message(), {}, (), None)
    ContinueProcessing.no

The 'stop' command is a synonym for 'end'.

    >>> command = config.commands['stop']
    >>> print command.name
    stop
    >>> print command.description
    An alias for 'end'.
    >>> command.argument_description
    ''
    >>> print command.process(mlist, Message(), {}, (), None)
    ContinueProcessing.no
