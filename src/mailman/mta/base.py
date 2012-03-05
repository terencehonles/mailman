# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Base delivery class."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BaseDelivery',
    'IndividualDelivery',
    ]


import copy
import socket
import logging
import smtplib

from zope.interface import implements

from mailman.config import config
from mailman.interfaces.mta import IMailTransportAgentDelivery
from mailman.mta.connection import Connection


log = logging.getLogger('mailman.smtp')



class BaseDelivery:
    """Base delivery class."""

    implements(IMailTransportAgentDelivery)

    def __init__(self):
        """Create a basic deliverer."""
        username = (config.mta.smtp_user if config.mta.smtp_user else None)
        password = (config.mta.smtp_pass if config.mta.smtp_pass else None)
        self._connection = Connection(
            config.mta.smtp_host, int(config.mta.smtp_port),
            int(config.mta.max_sessions_per_connection),
            username, password)

    def _deliver_to_recipients(self, mlist, msg, msgdata, recipients):
        """Low-level delivery to a set of recipients.

        :param mlist: The mailing list being delivered to.
        :type mlist: `IMailingList`
        :param msg: The original message being delivered.
        :type msg: `Message`
        :param msgdata: Additional message metadata for this delivery.
        :type msgdata: dictionary
        :param recipients: The recipients of this message.
        :type recipients: sequence
        :return: delivery failures as defined by `smtplib.SMTP.sendmail`
        :rtype: dictionary
        """
        # Do the actual sending.
        sender = self._get_sender(mlist, msg, msgdata)
        message_id = msg['message-id']
        try:
            refused = self._connection.sendmail(
                sender, recipients, msg.as_string())
        except smtplib.SMTPRecipientsRefused as error:
            log.error('%s recipients refused: %s', message_id, error)
            refused = error.recipients
        except smtplib.SMTPResponseException as error:
            log.error('%s response exception: %s', message_id, error)
            refused = dict(
                # recipient -> (code, error)
                (recipient, (error.smtp_code, error.smtp_error))
                for recipient in recipients)
        except (socket.error, IOError, smtplib.SMTPException) as error:
            # MTA not responding, or other socket problems, or any other
            # kind of SMTPException.  In that case, nothing got delivered,
            # so treat this as a temporary failure.  We use error code 444
            # for this (temporary, unspecified failure, cf RFC 5321).
            log.error('%s low level smtp error: %s', message_id, error)
            error = str(error)
            refused = dict(
                # recipient -> (code, error)
                (recipient, (444, error))
                for recipient in recipients)
        return refused

    def _get_sender(self, mlist, msg, msgdata):
        """Return the envelope sender to use.

        The message metadata can override the calculation of the sender, but
        otherwise it falls to the list's -bounces robot.  If this message is
        not intended for any specific mailing list, the site owner's address
        is used.

        :param mlist: The mailing list being delivered to.
        :type mlist: `IMailingList`
        :param msg: The original message being delivered.
        :type msg: `Message`
        :param msgdata: Additional message metadata for this delivery.
        :type msgdata: dictionary
        :return: The envelope sender.
        :rtype: string
        """
        sender = msgdata.get('sender')
        if sender is None:
            return (config.mailman.site_owner
                    if mlist is None
                    else mlist.bounces_address)
        return sender



class IndividualDelivery(BaseDelivery):
    """Deliver a unique individual message to each recipient.

    This is a framework delivery mechanism.  By using mixins, registration,
    and subclassing you can customize this delivery class to do any
    combination of VERP, full personalization, individualized header/footer
    decoration and even full mail merging.

    The core concept here is that for each recipient, the deliver() method
    iterates over the list of registered callbacks, each of which have a
    chance to modify the message before final delivery.
    """

    def __init__(self):
        """See `BaseDelivery`."""
        super(IndividualDelivery, self).__init__()
        self.callbacks = []

    def deliver(self, mlist, msg, msgdata):
        """See `IMailTransportAgentDelivery`.

        Craft a unique message for every recipient.  Encode the recipient's
        delivery address in the return envelope so there can be no ambiguity
        in bounce processing.
        """
        refused = {}
        recipients = msgdata.get('recipients', set())
        for recipient in recipients:
            log.debug('IndividualDelivery to: %s', recipient)
            # Make a copy of the original messages and operator on it, since
            # we're going to munge it repeatedly for each recipient.
            message_copy = copy.deepcopy(msg)
            msgdata_copy = msgdata.copy()
            # Squirrel the current recipient away in the message metadata.
            # That way the subclass's _get_sender() override can encode the
            # recipient address in the sender, e.g. for VERP.
            msgdata_copy['recipient'] = recipient
            # See if the recipient is a member of the mailing list, and if so,
            # squirrel this information away for use by other modules, such as
            # the header/footer decorator.  XXX 2012-03-05 this is probably
            # highly inefficient on the database.
            member = mlist.members.get_member(recipient)
            msgdata_copy['member'] = member
            for callback in self.callbacks:
                callback(mlist, message_copy, msgdata_copy)
            status = self._deliver_to_recipients(
                mlist, message_copy, msgdata_copy, [recipient])
            refused.update(status)
        return refused
