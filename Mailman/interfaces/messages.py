# Copyright (C) 2007 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""The message storage service."""

from zope.interface import Interface, Attribute



class IMessageStore(Interface):
    """The interface of the global message storage service.

    All messages that are stored in the system live in the message storage
    service.  This store is responsible for providing unique identifiers for
    every message stored in it.  A message stored in this service must have at
    least a Message-ID header and a Date header.  These are not guaranteed to
    be unique, so the service also provides a unique sequence number to every
    message.

    Storing a message returns the unique sequence number for the message.
    This sequence number will be stored on the message's
    X-List-Sequence-Number header.  Any previous such header value will be
    overwritten.  An X-List-ID-Hash header will also be added, containing the
    Base-32 encoded SHA1 hash of the message's Message-ID and Date headers.

    The combination of the X-List-ID-Hash header and the
    X-List-Sequence-Number header uniquely identify this message to the
    storage service.  A globally unique URL that addresses this message may be
    crafted from these headers and the List-Archive header as follows.  For a
    message with the following headers:

    Message-ID: <87myycy5eh.fsf@uwakimon.sk.tsukuba.ac.jp>
    Date: Wed, 04 Jul 2007 16:49:58 +0900
    List-Archive: http://archive.example.com/
    X-List-ID-Hash: RXTJ357KFOTJP3NFJA6KMO65X7VQOHJI
    X-List-Sequence-Number: 801

    the globally unique URL would be:

    http://archive.example.com/RXTJ357KFOTJP3NFJA6KMO65X7VQOHJI/801
    """

    def add(message):
        """Add the message to the store.

        :param message: An email.message.Message instance containing at least
            a Message-ID header and a Date header.  The message will be given
            an X-List-ID-Hash header and an X-List-Sequence-Number header.
        :returns: The message's sequence ID as an integer.
        :raises ValueError: if the message is missing one of the required
            headers.
        """

    def get_messages_by_message_id(message_id):
        """Return the set of messages with the matching Message-ID.

        :param message_id: The Message-ID header contents to search for.
        :returns: An iterator over all the matching messages.
        """

    def get_messages_by_hash(hash):
        """Return the set of messages with the matching X-List-ID-Hash.
        
        :param hash: The X-List-ID-Hash header contents to search for.
        :returns: An iterator over all the matching messages.
        """

    def get_message(global_id):
        """Return the message with the matching hash and sequence number.

        :param global_id: The global relative ID which uniquely addresses this
            message, relative to the base address of the message store.  This
            must be a string of the X-List-ID-Hash followed by a single slash
            character, followed by the X-List-Sequence-Number.
        :returns: The matching message, or None if there is no match.
        """

    def delete_message(global_id):
        """Remove the addressed message from the store.

        :param global_id: The global relative ID which uniquely addresses the
            message to delete.
        :raises KeyError: if there is no such message.
        """

    messages = Attribute(
        """An iterator over all messages in this message store.""")



class IMessage(Interface):
    """The representation of an email message."""

    hash = Attribute("""The unique SHA1 hash of the message.""")

    path = Attribute("""The filesystem path to the message object.""")

    message_id = Attribute("""The message's Message-ID header.""")
