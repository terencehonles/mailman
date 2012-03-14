========================================
Notes from the PyCon 2012 Mailman Sprint
========================================

.. authorship
   The notes are based on Barry Warsaw's description of the Mailman 3
   pipeline at the PyCon 2012 Mailman sprint on March 13, with
   diagrams from his "Mailman" presentation at PyCon 2012.
   Transcribed by Stephen Turnbull.

These are notes from the Mailman sprint at PyCon 2012.  They are not
terribly well organized, nor fully fleshed out.  Please edit and push
branches to Launchpad at lp:mailman or post patches to <WHERE?> <URL?>.

The intent of this document is to provide a view of Mailman 3's
workflow and structures from "eight miles high".


Basic Messaging Handling Workflow
---------------------------------

Mailman accepts a message via the LMTP protocol (RFC 2033).  It
implements a simple LMTP server internally based on the LMTP server
provided in the Python stdlib.  The LMTP server's responsibility is to
parse the message into a tuple (*mlist*, *msg*, *msg_data*).  If the
parse fails (including messages which Mailman considers to be invalid
due to lack of Message-Id as strongly recommended by RFC 2822 and RFC
5322), the message will be rejected, otherwise the tuple is pickled,
and the resulting *message pickle* added to one of the IN, COMMAND, or
BOUNCE processing queues.

.. graphviz::

   digraph msgflow {
     rankdir = LR;
     node [shape=box, color=lightblue, style=filled];
     msg [shape=ellipse, color=black, fillcolor=white];
     lmtpd [label="LMTP\nSERVER"];
     msg -> MTA [label="SMTP"];
     MTA -> lmtpd [label="LMTP"];
     lmtpd -> MTA [label="reject"];
     lmtpd -> IN -> POSTING [label=".pck"];
     lmtpd -> BOUNCES [label=".pck"];
     lmtpd -> COMMAND [label=".pck"];
   }

The IN queue is processed by *filter chains* (explained below) to
determine whether the post (or administrative request) will be
processed.  If not allowed, the message pickle is discarded, rejected
(returned to sender), or held (added to the MODERATION queue -- not
shown).  Otherwise the message is added to the POSTING queue.

Each of the COMMAND, BOUNCE, and POSTING queues is processed by a
*pipeline of handlers* as in Mailman 2's pipeline.  (Some functions
such as spam detection that were handled in the Mailman 2 pipeline are
now in the filter chains.)

Handlers may copy messages to other queues (*e.g.*, ARCHIVE), and
eventually posts for distribution end up in the OUT queue for
injection into the MTA.

The VIRGIN queue is a special queue for messages created by Mailman.

.. image:: pipeline.png
   :scale: 67

.. graphviz::

   digraph pipeline {
   }


Message Filtering
-----------------

Once a message has been classified as a post or administrivia, rules
are applied to determine whether the message should be distributed or
acted on.  Rules include things like "if the message's sender is a
non-member, hold it for moderation", or "if the message contains an
Approved field with a valid password, distribute it".  A rule may also
make no decision, in which case the message pickle is passed on to the
next rule in the filter chain.

.. image:: chains.png
   :scale: 67

..   builtin chain [shape=none]
     accept chain [shape=none]
     hold chain [shape=none]
     discard chain [shape=none]
     moderation chain [shape=none]

.. graphviz::

   digraph chains {
     rankdir=LR;
     approved [shape=record, label="<f0> approved | {<f1> | <f2>}"];
     emergency [shape=record, label="<f0> emergency | {<f1> | <f2>}"];
     loop [shape=record, label="<f0> loop | {<f1> | <f2>}"];
     modmember [shape=record, label="<f0> moderate\nmember | {<f1> | <f2>}"];
     administrivia [shape=record, label="<f0> administrivia | <f1>"];
     maxsize [shape=record, label="<f0> max\ size | {<f1> | <f2>}"];
     any [shape=record, label="<f0> any | {<f1> | <f2>}"];
     truth [shape=record, label="<f0> truth | <f1>"];
     IN [shape=box, color=lightblue, style=filled, rank=source];
     IN -> approved;
     subgraph fubar {
       subgraph bar {
         /* rankdir=TB; */
         rank=same;
         approved:f2 -> emergency;
         emergency:f2 -> loop;
         loop:f2 -> modmember;
         modmember:f2 -> administrivia;
         administrivia:f2 -> maxsize;
         maxsize:f2 -> any;
         any:f2 -> truth;
       };
       subgraph foo {
         /* rankdir=TB; */
         rank=same;
         APPROVED [shape=box, color=lightblue, style=filled];
         POSTING [shape=box, color=lightblue, style=filled];
         MODERATION [shape=box, color=lightblue, style=filled];
         DISCARD [shape=trapezoidium, color=lightblue, style=filled];
       };
     };
     approved:f1 -> POSTING;
     emergency:f1 -> MODERATION;
     loop:f1 -> DISCARD;
     modmember:f1 -> MODERATION;
     maxsize:f1 -> MODERATION;
     any:f1 -> MODERATION;
     truth -> POSTING;
   }


Configuration
-------------

Uses lazr.config.

Each Runner's configuration object knows whether it should be started
when the Mailman daemon starts, and what queue the Runner manages.


Shell Commands
--------------

bin/mailman: This is an ubercommand, with subcommands for all the
various things admins might want to do, similar to mailmanctl, but
with more functionality.

bin/master: The runner manager: starts, watches, stops the runner
daemons.

bin/runner: Individual runner daemons.  Each instance is configured
with a configure object specified on the command line, and other
command line options.


User Model
----------

A *user* represents a person.  A user has an *id* and a *display
name*, and a list of addresses.

Each *address* is a separate object, linked to a user with a user id.

A list *member* is a link from a user to a mailing list.  Each list
member has a user id, a mailing list name, an address (which may be
None, which will be replaced by the user's preferred address, a list
of preferences, and a *role* such as "owner" or "moderator".  Roles
are used to determine what kinds of mail the user receives via that
membership.  *Owners* will receive mail to *list*-owner, but not posts
and moderation traffic, for example.  A user with multiple roles on a
single list will theref1re have multiple memberships in that list, one
for each role.

Roles are implemented by "magical, invisible" *rosters*.


List Styles
-----------

Each list *style* is a named object.  Its attributes are functions
used to apply the relevant style settings to the mailing list *at
creation time*.  Since these are functions, they can be composed in
various ways, to create substyles, *etc*.
