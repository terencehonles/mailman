# Copyright (C) 2001,2002 by the Free Software Foundation, Inc.
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

"""Personalize the email message for delivery to each individual recipient.
"""

from Mailman import mm_cfg
from Mailman.Queue.sbcache import get_switchboard



def process(mlist, msg, msgdata):
    if not mlist.personalize or msgdata.get('personalized'):
        return
    # Make a copy for each recipient, and re-queue the copies to the incoming
    # queue.  Set the pipeline for the copies to just Decorate and
    # ToOutgoing.  The normal queue on the original copy should take care of
    # everything else.
    newpipeline = ['Decorate', 'ToOutgoing']
    inq = get_switchboard(mm_cfg.INQUEUE_DIR)
    # Save the original To: line
    originalto = msg['To']
    # Create a separate message for each recipient
    for member in msgdata.get('recips', []):
        metadatacopy = msgdata.copy()
        metadatacopy['pipeline'] = newpipeline
        metadatacopy['recips'] = [member]
        metadatacopy['personalized'] = 1
        del msg['To']
        name = mlist.getMemberName(member)
        if name:
            msg['To'] = '%s (%s)' % (member, name)
        else:
            msg['To'] = member
        # We can flag the mail as a duplicate for each member, if they've
        # already received that message. (See AvoidDuplicates.py).  First,
        # delete any existing such header first
        del msg['x-mailman-copy']
        if msgdata.get('add-dup-header', {}).has_key(member):
            msg['X-Mailman-Copy'] = 'yes'

        # See if we're taking the opportunity to VERP for more reliable bounce
        # processing.
        metadatacopy['verp'] = mm_cfg.VERP_PERSONALIZED_DELIVERIES
        inq.enqueue(msg, metadatacopy, listname=mlist.internal_name())
    # Restore the original To: line
    del msg['To']
    msg['To'] = originalto
    # The original message is not a copy.
    del msg['x-mailman-copy']
    # Don't let the normal ToOutgoing processing actually send the original
    # copy, otherwise we'll get copys.
    del msgdata['recips']
