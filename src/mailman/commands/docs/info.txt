===================
Getting information
===================

You can get information about Mailman's environment by using the command line
script ``mailman info``.  By default, the info is printed to standard output.
::

    >>> from mailman.commands.cli_info import Info
    >>> command = Info()

    >>> class FakeArgs:
    ...     output = None
    ...     verbose = None
    >>> args = FakeArgs()

    >>> command.process(args)
    GNU Mailman 3...
    Python ...
    ...
    config file: .../test.cfg
    db url: sqlite:.../mailman.db
    REST root url: http://localhost:9001/3.0/
    REST credentials: restadmin:restpass

By passing in the ``-o/--output`` option, you can print the info to a file.

    >>> from mailman.config import config
    >>> import os
    >>> output_path = os.path.join(config.VAR_DIR, 'output.txt')
    >>> args.output = output_path
    >>> command.process(args)
    >>> with open(output_path) as fp:
    ...     print fp.read()
    GNU Mailman 3...
    Python ...
    ...
    config file: .../test.cfg
    db url: sqlite:.../mailman.db
    REST root url: http://localhost:9001/3.0/
    REST credentials: restadmin:restpass

You can also get more verbose information, which contains a list of the file
system paths that Mailman is using.

    >>> args.output = None
    >>> args.verbose = True
    >>> config.create_paths = False
    >>> config.push('fhs', """
    ... [mailman]
    ... layout: fhs
    ... """)
    >>> config.create_paths = True

The File System Hierarchy layout is the same every by definition.

    >>> command.process(args)
    GNU Mailman 3...
    Python ...
    ...
    File system paths:
        BIN_DIR                  = /sbin
        DATA_DIR                 = /var/lib/mailman/data
        ETC_DIR                  = /etc
        EXT_DIR                  = /etc/mailman.d
        LIST_DATA_DIR            = /var/lib/mailman/lists
        LOCK_DIR                 = /var/lock/mailman
        LOCK_FILE                = /var/lock/mailman/master.lck
        LOG_DIR                  = /var/log/mailman
        MESSAGES_DIR             = /var/lib/mailman/messages
        PID_FILE                 = /var/run/mailman/master.pid
        PRIVATE_ARCHIVE_FILE_DIR = /var/lib/mailman/archives/private
        PUBLIC_ARCHIVE_FILE_DIR  = /var/lib/mailman/archives/public
        QUEUE_DIR                = /var/spool/mailman
        TEMPLATE_DIR             = .../mailman/templates
        VAR_DIR                  = /var/lib/mailman


Clean up
========

    >>> config.pop('fhs')
