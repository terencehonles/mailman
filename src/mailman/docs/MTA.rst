===========================
Hooking up your mail server
===========================

Mailman needs to be hooked up to your mail server both to accept incoming mail
and to deliver outgoing mail.  Mailman itself never delivers messages to the
end user; it lets its immediate upstream mail server do that.

The preferred way to allow Mailman to accept incoming messages from your mail
server is to use the `Local Mail Transfer Protocol`_ (LMTP_) interface.  Most
open source mail server support LMTP for local delivery, and this is much more
efficient than spawning a process just to do the delivery.

Your mail server should also accept `Simple Mail Transfer Protocol`_ (SMTP_)
connections from Mailman, for all outgoing messages.

The specific instructions for hooking your mail server up to Mailman differs
depending on which mail server you're using.  The following are instructions
for the popular open source mail servers.

Note that Mailman provides lots of configuration variables that you can use to
tweak performance for your operating environment.  See the
`src/mailman/config/schema.cfg` file for details.


Exim
====

Contributions are welcome!


Postfix
=======

Mailman settings
----------------

You need to tell Mailman that you are using the Postfix mail server.  In your
`mailman.cfg` file, add the following section::

    [mta]
    incoming: mailman.mta.postfix.LMTP
    outgoing: mailman.mta.deliver.deliver
    lmtp_host: mail.example.com
    lmtp_port: 8024
    smtp_host: mail.example.com
    smtp_port: 25

Some of these settings are already the default, so take a look at Mailman's
`src/mailman/config/schema.cfg` file for details.  You'll need to change the
`lmtp_host` and `smtp_host` to the appropriate host names of course.
Generally, Postfix will listen for incoming SMTP connections on port 25.
Postfix will deliver via LMTP over port 24 by default, however if you are not
running Mailman as root, you'll need to change this to a higher port number,
as shown above.


Basic Postfix connections
-------------------------

There are several ways to hook Postfix_ up to Mailman, so here are the
simplest instructions.  The following settings should be added to Postfix's
`main.cf` file.

Mailman supports a technique called `Variable Envelope Return Path`_ (VERP) to
disambiguate and accurately record bounces.  By default Mailman's VERP
delimiter is the `+` sign, so adding this setting allows Postfix to properly
handle Mailman's VERP'd messages::

    # Support the default VERP delimiter.
    recipient_delimiter = +

In older versions of Postfix, unknown local recipients generated a temporary
failure.  It's much better (and the default in newer Postfix releases) to
treat them as permanent failures.  You can add this to your `main.cf` file if
needed (use the `postconf`_ to check the defaults)::

    unknown_local_recipient_reject_code = 550

While generally not necessary if you set `recipient_delimiter` as described
above, it's better for Postfix to not treat `owner-` and `-request` addresses
specially::

    owner_request_special = no


Transport maps
--------------

By default, Mailman works well with Postfix transport maps as a way to deliver
incoming messages to Mailman's LMTP server.  Mailman will automatically write
the correct transport map when its `bin/mailman genaliases` command is run, or
whenever a mailing list is created or removed via other commands.  To connect
Postfix to Mailman's LMTP server, add the following to Postfix's `main.cf`
file::

    transport_maps =
        hash:/path-to-mailman/var/data/postfix_lmtp
    local_recipient_maps =
        hash:/path-to-mailman/var/data/postfix_lmtp

where `path-to-mailman` is replaced with the actual path that you're running
Mailman from.  Setting `local_recipient_maps` as well as `transport_maps`
allows Postfix to properly reject all messages destined for non-existent local
users.


Virtual domains
---------------

TBD: figure out how virtual domains interact with the transport maps.


Sendmail
========

Contributions are welcome!


.. _`Local Mail Transfer Protocol`:
   http://en.wikipedia.org/wiki/Local_Mail_Transfer_Protocol
.. _LMTP: http://www.faqs.org/rfcs/rfc2033.html
.. _`Simple Mail Transfer Protocol`:
   http://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol
.. _SMTP: http://www.faqs.org/rfcs/rfc5321.html
.. _Postfix: http://www.postfix.org
.. _`Variable Envelope Return Path`:
   http://en.wikipedia.org/wiki/Variable_envelope_return_path
.. _postconf: http://www.postfix.org/postconf.1.html
