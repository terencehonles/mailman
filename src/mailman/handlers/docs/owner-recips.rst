=====================
List owner recipients
=====================

When a message is posted to a mailing list's `-owners` address, all of the
list's administrators will receive a copy.  The administrators are defined as
the set of owners and moderators.

    >>> mlist_1 = create_list('alpha@example.com')

Anne is the owner of the list and Bart is a moderator of the list.

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)
    >>> anne_addr = user_manager.create_address('anne@example.com')
    >>> bart_addr = user_manager.create_address('bart@example.com')
    >>> from mailman.interfaces.member import MemberRole
    >>> anne = mlist_1.subscribe(anne_addr, MemberRole.owner)
    >>> bart = mlist_1.subscribe(bart_addr, MemberRole.moderator)

The recipients list for the `-owners` address includes both Anne and Bart.

    >>> msg = message_from_string("""\
    ... From: Xavier Person <xperson@example.com>
    ... To: alpha@example.com
    ...
    ... """)
    >>> msgdata = {}
    >>> handler = config.handlers['owner-recipients']
    >>> handler.process(mlist_1, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    anne@example.com
    bart@example.com

Anne disables her owner delivery, so she will not receive `-owner` emails.

    >>> from mailman.interfaces.member import DeliveryStatus
    >>> anne.preferences.delivery_status = DeliveryStatus.by_user
    >>> msgdata = {}
    >>> handler.process(mlist_1, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    bart@example.com
    
If Bart also disables his owner delivery, then no one could contact the list's
owners.  Since this is unacceptable, the site owner is used as a fallback.

    >>> bart.preferences.delivery_status = DeliveryStatus.by_user
    >>> msgdata = {}
    >>> handler.process(mlist_1, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    noreply@example.com

For mailing lists which have no owners at all, the site owner is also used as
a fallback.

    >>> mlist_2 = create_list('beta@example.com')
    >>> mlist_2.administrators.member_count
    0
    >>> msgdata = {}
    >>> handler.process(mlist_2, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    noreply@example.com
