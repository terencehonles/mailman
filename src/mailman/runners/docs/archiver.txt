=========
Archiving
=========

Mailman can archive to any number of archivers that adhere to the
``IArchiver`` interface.  By default, there's a Pipermail archiver.
::

    >>> mlist = create_list('test@example.com')
    >>> transaction.commit()

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: My first post
    ... Message-ID: <first>
    ...
    ... First post!
    ... """)

    >>> archiver_queue = config.switchboards['archive']
    >>> ignore = archiver_queue.enqueue(msg, {}, listname=mlist.fqdn_listname)

    >>> from mailman.runners.archive import ArchiveRunner
    >>> from mailman.testing.helpers import make_testable_runner
    >>> runner = make_testable_runner(ArchiveRunner)
    >>> runner.run()

    # The best we can do is verify some landmark exists.  Let's use the
    # Pipermail pickle file exists.
    >>> listname = mlist.fqdn_listname
    >>> import os
    >>> os.path.exists(os.path.join(
    ...     config.PUBLIC_ARCHIVE_FILE_DIR, listname, 'pipermail.pck'))
    True
