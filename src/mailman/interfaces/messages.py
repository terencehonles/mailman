# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""The message storage service."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IMessage',
    'IMessageStore',
    ]


from zope.interface import Interface, Attribute



class IMessageStore(Interface):
    """The interface of the global message storage service.

    All messages that are stored in the system live in the message storage
    service.  A message stored in this service must have a Message-ID header.
    The store writes an X-Message-ID-Hash header which contains the Base32
    encoded SHA1 hash of the message's Message-ID header.  Any existing
    X-Message-ID-Hash header is overwritten.

    Either the Message-ID or the X-Message-ID-Hash header can be used to
    uniquely identify this message in the storage service.  While it is
    possible to see duplicate Message-IDs, this is never correct and the
    service is allowed to drop any subsequent colliding messages, or overwrite
    earlier messages with later ones.

    The combination of the List-Archive header and either the Message-ID or
    X-Message-ID-Hash header can be used to retrieve the message from the
    internet facing interface for the message store.  This can be considered a
    globally unique URI to the message.

    For example, a message with the following headers:

    Message-ID: <87myycy5eh.fsf@uwakimon.sk.tsukuba.ac.jp>
    Date: Wed, 04 Jul 2007 16:49:58 +0900
    List-Archive: http://archive.example.com/
    X-Message-ID-Hash: RXTJ357KFOTJP3NFJA6KMO65X7VQOHJI

    the globally unique URI would be:

    http://archive.example.com/RXTJ357KFOTJP3NFJA6KMO65X7VQOHJI
    """

    def add(message):
        """Add the message to the store.

        :param message: An email.message.Message instance containing at least
            a unique Message-ID header.  The message will be given an
            X-Message-ID-Hash header, overriding any existing such header.
        :returns: The calculated X-Message-ID-Hash header.
        :raises ValueError: if the message is missing a Message-ID header.
            The storage service is also allowed to raise this exception if it
            find, but disallows collisions.
        """

    def get_message_by_id(message_id):
        """Return the message with a matching Message-ID.

        :param message_id: The Message-ID header contents to search for.
        :returns: The message, or None if no matching message was found.
        """

    def get_message_by_hash(message_id_hash):
        """Return the message with the matching X-Message-ID-Hash.
        
        :param message_id_hash: The X-Message-ID-Hash header contents to
            search for.
        :returns: The message, or None if no matching message was found.
        """

    def delete_message(message_id):
        """Remove the given message from the store.

        :param message: The Message-ID of the mesage to delete from the store.
        :raises LookupError: if there is no such message.
        """

    messages = Attribute(
        """An iterator over all messages in this message store.""")



class IMessage(Interface):
    """The representation of an email message."""

    message_id = Attribute("""The message's Message-ID header.""")

    message_id_hash = Attribute("""The unique SHA1 hash of the message.""")

    path = Attribute("""The filesystem path to the message object.""")
