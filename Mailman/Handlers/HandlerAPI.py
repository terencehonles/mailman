# Copyright (C) 1998 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Contains all the common functionality for the msg handler API."""

class HandlerError(Exception):
    """Base class for all handler errors"""
    pass


class MessageHeld(HandlerError):
    """Base class for all message-being-held short circuits"""
    pass



# for messages that arrive from the outside, to be delivered to all mailing
# list subscribers
def DeliverToList(mlist, msg):
    pipeline = ['SpamDetect',
                'Approve',
                'Hold',
                'Cleanse',
                'CookHeaders',
                'ToDigest',
                'ToArchive',
                'ToUsenet',
                'CalcRecips',
                'Decorate',
                'Sendmail',
                'Acknowledge',
                'AfterDelivery',
                ]
    for modname in pipeline:
        mod = __import__('Mailman.Handlers.'+modname)
        func = getattr(getattr(getattr(mod, 'Handlers'), modname), 'process')
        try:
            func(mlist, msg)
        except MessageHeld:
            break



# for messages crafted internally by the Mailman system.  The msg object
# should have already calculated and set msg.recips.  TBD: can the mlist be
# None?
def DeliverToUser(mlist, msg):
    pipeline = ['CookHeaders',
                'Sendmail',
                ]
    msg.fastrack = 1
    for modname in pipeline:
        mod = __import__('Mailman.Handlers.'+modname)
        func = getattr(getattr(getattr(mod, 'Handlers'), modname), 'process')
        # None of these modules should ever generate a MessageHeld exception
        func(mlist, msg)
