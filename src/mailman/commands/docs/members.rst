================
Managing members
================

The ``bin/mailman members`` command allows a site administrator to display,
add, and remove members from a mailing list.
::

    >>> mlist1 = create_list('test1@example.com')

    >>> class FakeArgs:
    ...     input_filename = None
    ...     output_filename = None
    ...     listname = []
    ...     regular = False
    ...     digest = None
    ...     nomail = None
    >>> args = FakeArgs()

    >>> from mailman.commands.cli_members import Members
    >>> command = Members()


Listing members
===============

You can list all the members of a mailing list by calling the command with no
options.  To start with, there are no members of the mailing list.

    >>> args.listname = [mlist1.fqdn_listname]
    >>> command.process(args)
    test1@example.com has no members

Once the mailing list add some members, they will be displayed.
::

    >>> from mailman.interfaces.member import DeliveryMode
    >>> from mailman.app.membership import add_member
    >>> add_member(mlist1, 'anne@example.com', 'Anne Person', 'xxx',
    ...            DeliveryMode.regular, mlist1.preferred_language.code)
    <Member: Anne Person <anne@example.com>
             on test1@example.com as MemberRole.member>
    >>> add_member(mlist1, 'bart@example.com', 'Bart Person', 'xxx',
    ...            DeliveryMode.regular, mlist1.preferred_language.code)
    <Member: Bart Person <bart@example.com>
             on test1@example.com as MemberRole.member>

    >>> command.process(args)
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>

Members are displayed in alphabetical order based on their address.
::

    >>> add_member(mlist1, 'anne@aaaxample.com', 'Anne Person', 'xxx',
    ...            DeliveryMode.regular, mlist1.preferred_language.code)
    <Member: Anne Person <anne@aaaxample.com>
             on test1@example.com as MemberRole.member>

    >>> command.process(args)
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>

You can also output this list to a file.

    >>> from tempfile import mkstemp
    >>> fd, args.output_filename = mkstemp()
    >>> import os
    >>> os.close(fd)
    >>> command.process(args)
    >>> with open(args.output_filename) as fp:
    ...     print fp.read()
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>
    >>> os.remove(args.output_filename)
    >>> args.output_filename = None

The output file can also be standard out.

    >>> args.output_filename = '-'
    >>> command.process(args)
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>
    >>> args.output_filename = None


Filtering on delivery mode
--------------------------

You can limit output to just the regular non-digest members...

    >>> args.regular = True
    >>> member = mlist1.members.get_member('anne@example.com')
    >>> member.preferences.delivery_mode = DeliveryMode.plaintext_digests
    >>> command.process(args)
    Anne Person <anne@aaaxample.com>
    Bart Person <bart@example.com>

...or just the digest members.  Furthermore, you can either display all digest
members...

    >>> member = mlist1.members.get_member('anne@aaaxample.com')
    >>> member.preferences.delivery_mode = DeliveryMode.mime_digests
    >>> args.regular = False
    >>> args.digest = 'any'
    >>> command.process(args)
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>

...just plain text digest members...

    >>> args.digest = 'plaintext'
    >>> command.process(args)
    Anne Person <anne@example.com>

...just MIME digest members.
::

    >>> args.digest = 'mime'
    >>> command.process(args)
    Anne Person <anne@aaaxample.com>

    # Reset for following tests.
    >>> args.digest = None


Filtering on delivery status
----------------------------

You can also filter the display on the member's delivery status.  By default,
all members are displayed, but you can filter out only those whose delivery
status is enabled...
::

    >>> from mailman.interfaces.member import DeliveryStatus
    >>> member = mlist1.members.get_member('anne@aaaxample.com')
    >>> member.preferences.delivery_status = DeliveryStatus.by_moderator
    >>> member = mlist1.members.get_member('bart@example.com')
    >>> member.preferences.delivery_status = DeliveryStatus.by_user
    >>> member = add_member(
    ...     mlist1, 'cris@example.com', 'Cris Person', 'xxx',
    ...     DeliveryMode.regular, mlist1.preferred_language.code)
    >>> member.preferences.delivery_status = DeliveryStatus.unknown
    >>> member = add_member(
    ...     mlist1, 'dave@example.com', 'Dave Person', 'xxx',
    ...     DeliveryMode.regular, mlist1.preferred_language.code)
    >>> member.preferences.delivery_status = DeliveryStatus.enabled
    >>> member = add_member(
    ...     mlist1, 'elly@example.com', 'Elly Person', 'xxx',
    ...     DeliveryMode.regular, mlist1.preferred_language.code)
    >>> member.preferences.delivery_status = DeliveryStatus.by_bounces

    >>> args.nomail = 'enabled'
    >>> command.process(args)
    Anne Person <anne@example.com>
    Dave Person <dave@example.com>

...or disabled by the user...

    >>> args.nomail = 'byuser'
    >>> command.process(args)
    Bart Person <bart@example.com>

...or disabled by the list administrator (or moderator)...

    >>> args.nomail = 'byadmin'
    >>> command.process(args)
    Anne Person <anne@aaaxample.com>

...or by the bounce processor...

    >>> args.nomail = 'bybounces'
    >>> command.process(args)
    Elly Person <elly@example.com>

...or for unknown (legacy) reasons.

    >>> args.nomail = 'unknown'
    >>> command.process(args)
    Cris Person <cris@example.com>

You can also display all members who have delivery disabled for any reason.
::

    >>> args.nomail = 'any'
    >>> command.process(args)
    Anne Person <anne@aaaxample.com>
    Bart Person <bart@example.com>
    Cris Person <cris@example.com>
    Elly Person <elly@example.com>

    # Reset for following tests.
    >>> args.nomail = None


Adding members
==============

You can add members to a mailing list from the command line.  To do so, you
need a file containing email addresses and full names that can be parsed by
``email.utils.parseaddr()``.
::

    >>> mlist2 = create_list('test2@example.com')

    >>> import os
    >>> path = os.path.join(config.VAR_DIR, 'addresses.txt')
    >>> with open(path, 'w') as fp:
    ...     for address in ('aperson@example.com',
    ...                     'Bart Person <bperson@example.com>',
    ...                     'cperson@example.com (Cate Person)',
    ...                     ):
    ...         print >> fp, address

    >>> args.input_filename = path
    >>> args.listname = [mlist2.fqdn_listname]
    >>> command.process(args)

    >>> from operator import attrgetter
    >>> dump_list(mlist2.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>

You can also specify ``-`` as the filename, in which case the addresses are
taken from standard input.
::

    >>> from StringIO import StringIO
    >>> fp = StringIO()
    >>> fp.encoding = 'us-ascii'
    >>> for address in ('dperson@example.com',
    ...                 'Elly Person <eperson@example.com>',
    ...                 'fperson@example.com (Fred Person)',
    ...                 ):
    ...         print >> fp, address
    >>> fp.seek(0)
    >>> import sys
    >>> sys.stdin = fp

    >>> args.input_filename = '-'
    >>> command.process(args)
    >>> sys.stdin = sys.__stdin__

    >>> dump_list(mlist2.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>

Blank lines and lines that begin with '#' are ignored.
::

    >>> with open(path, 'w') as fp:
    ...     for address in ('gperson@example.com',
    ...                     '# hperson@example.com',
    ...                     '   ',
    ...                     '',
    ...                     'iperson@example.com',
    ...                     ):
    ...         print >> fp, address

    >>> args.input_filename = path
    >>> command.process(args)
    >>> dump_list(mlist2.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com

Addresses which are already subscribed are ignored, although a warning is
printed.
::

    >>> with open(path, 'w') as fp:
    ...     for address in ('gperson@example.com',
    ...                     'aperson@example.com',
    ...                     'jperson@example.com',
    ...                     ):
    ...         print >> fp, address

    >>> command.process(args)
    Already subscribed (skipping): gperson@example.com
    Already subscribed (skipping): aperson@example.com

    >>> dump_list(mlist2.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com
    jperson@example.com


Displaying members
==================

With no arguments, the command displays all members of the list.

    >>> args.input_filename = None
    >>> command.process(args)
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com
    jperson@example.com
