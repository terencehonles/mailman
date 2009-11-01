# Copyright (C) 2009 by the Free Software Foundation, Inc.
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
    ]


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

    def __init__(self, max_recipients=None):
        """Create a basic deliverer.

        :param max_recipients: The maximum number of recipients per delivery
            chunk.  None, zero or less means to group all recipients into one
            big chunk.
        :type max_recipients: integer
        """
        self._max_recipients = (max_recipients
                                if max_recipients is not None
                                else 0)
        self._connection = Connection(
            config.mta.smtp_host, int(config.mta.smtp_port),
            self._max_recipients)

    def _deliver_to_recipients(self, mlist, msg, msgdata,
                               sender, recipients):
        """Low-level delivery to a set of recipients.

        :param mlist: The mailing list being delivered to.
        :type mlist: `IMailingList`
        :param msg: The original message being delivered.
        :type msg: `Message`
        :param msgdata: Additional message metadata for this delivery.
        :type msgdata: dictionary
        :param sender: The envelope sender.
        :type sender: string
        :param recipients: The recipients of this message.
        :type recipients: sequence
        :return: delivery failures as defined by `smtplib.SMTP.sendmail`
        :rtype: dictionary
        """
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
