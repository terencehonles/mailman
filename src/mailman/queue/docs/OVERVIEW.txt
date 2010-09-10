==============
Alias Overview
==============

A typical Mailman list exposes nine aliases which point to seven different
wrapped scripts.  E.g. for a list named ``mylist``, you'd have::

    mylist-bounces -> bounces
    mylist-confirm -> confirm
    mylist-join    -> join    (-subscribe is an alias)
    mylist-leave   -> leave   (-unsubscribe is an alias)
    mylist-owner   -> owner
    mylist         -> post
    mylist-request -> request

``-request``, ``-join``, and ``-leave`` are a robot addresses; their sole
purpose is to process emailed commands, although the latter two are hardcoded
to subscription and unsubscription requests.  ``-bounces`` is the automated
bounce processor, and all messages to list members have their return address
set to ``-bounces``.  If the bounce processor fails to extract a bouncing
member address, it can optionally forward the message on to the list owners.

``-owner`` is for reaching a human operator with minimal list interaction
(i.e. no bounce processing).  ``-confirm`` is another robot address which
processes replies to VERP-like confirmation notices.

So delivery flow of messages look like this::

    joerandom ---> mylist ---> list members
       |                           |
       |                           |[bounces]
       |        mylist-bounces <---+ <-------------------------------+
       |              |                                              |
       |              +--->[internal bounce processing]              |
       |              ^                |                             |
       |              |                |    [bounce found]           |
       |         [bounces *]           +--->[register and discard]   |
       |              |                |                      |      |
       |              |                |                      |[*]   |
       |        [list owners]          |[no bounce found]     |      |
       |              ^                |                      |      |
       |              |                |                      |      |
       +-------> mylist-owner <--------+                      |      |
       |                                                      |      |
       |           data/owner-bounces.mbox <--[site list] <---+      |
       |                                                             |
       +-------> mylist-join--+                                      |
       |                      |                                      |
       +------> mylist-leave--+                                      |
       |                      |                                      |
       |                      v                                      |
       +-------> mylist-request                                      |
       |              |                                              |
       |              +---> [command processor]                      |
       |                            |                                |
       +-----> mylist-confirm ----> +---> joerandom                  |
                                              |                      |
                                              |[bounces]             |
                                              +----------------------+

A person can send an email to the list address (for posting), the ``-owner``
address (to reach the human operator), or the ``-confirm``, ``-join``,
``-leave``, and ``-request`` mailbots.  Message to the list address are then
forwarded on to the list membership, with bounces directed to the -bounces
address.

[*] Messages sent to the ``-owner`` address are forwarded on to the list
owner/moderators.  All ``-owner`` destined messages have their bounces
directed to the site list ``-bounces`` address, regardless of whether a human
sent the message or the message was crafted internally.  The intention here is
that the site owners want to be notified when one of their list owners'
addresses starts bouncing (yes, the will be automated in a future release).

Any messages to site owners has their bounces directed to a special *loop
killer* address, which just dumps the message into
``data/owners-bounces.mbox``.

Finally, message to any of the mailbots causes the requested action to be
performed.  Results notifications are sent to the author of the message, which
all bounces pointing back to the -bounces address.
