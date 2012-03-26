===================
Dumping queue files
===================

The ``qfile`` command dumps the contents of a queue pickle file.  This is
especially useful when you have shunt files you want to inspect.

XXX Test the interactive operation of qfile


Pretty printing
===============

By default, the ``qfile`` command pretty prints the contents of a queue pickle
file to standard output.
::

    >>> from mailman.commands.cli_qfile import QFile
    >>> command = QFile()

    >>> class FakeArgs:
    ...     interactive = False
    ...     doprint = True
    ...     qfile = []

Let's say Mailman shunted a message file.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: Uh oh
    ...
    ... I borkeded Mailman.
    ... """)

    >>> shuntq = config.switchboards['shunt']
    >>> basename = shuntq.enqueue(msg, foo=7, bar='baz', bad='yes')

Once we've figured out the file name of the shunted message, we can print it.
::

    >>> from os.path import join
    >>> qfile = join(shuntq.queue_directory, basename + '.pck')

    >>> FakeArgs.qfile = [qfile]
    >>> command.process(FakeArgs)
    [----- start pickle -----]
    <----- start object 1 ----->
    From nobody ...
    From: aperson@example.com
    To: test@example.com
    Subject: Uh oh
    <BLANKLINE>
    I borkeded Mailman.
    <BLANKLINE>
    <----- start object 2 ----->
    {   u'_parsemsg': False,
        'bad': u'yes',
        'bar': u'baz',
        'foo': 7,
        u'version': 3}
    [----- end pickle -----]

Maybe we don't want to print the contents of the file though, in case we want
to enter the interactive prompt.

    >>> FakeArgs.doprint = False
    >>> command.process(FakeArgs)
