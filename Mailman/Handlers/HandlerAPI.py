# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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

import traceback
import time

from Mailman import mm_cfg
from Mailman import Errors
from Mailman.pythonlib.StringIO import StringIO



# Exception classes for this subsystem.
class HandlerError(Errors.MailmanError):
    """Base class for all handler errors."""

class MessageHeld(HandlerError):
    """Base class for all message-being-held short circuits."""
    def __str__(self):
        return self.__class__.__doc__

class DiscardMessage(HandlerError):
    """The message can be discarded with no further action"""

class SomeRecipientsFailed(HandlerError):
    """Delivery to some or all recipients failed"""



# All messages which are delivered to the entire list membership go through
# this pipeline of handler modules.
LIST_PIPELINE = ['SpamDetect',
                 'Approve',
                 'Replybot',
                 'Hold',
                 'Cleanse',
                 'CookHeaders',
                 'ToDigest',
                 'ToArchive',
                 'ToUsenet',
                 'CalcRecips',
                 'Decorate',
                 mm_cfg.DELIVERY_MODULE,
                 'AfterDelivery',
                 'Acknowledge',
                 ]



# Central mail delivery handler
def DeliverToList(mlist, msg, msgdata):
    pipeline = msgdata.get('pipeline', LIST_PIPELINE)
    while pipeline:
        modname = pipeline.pop(0)
        mod = __import__('Mailman.Handlers.' + modname)
        func = getattr(getattr(getattr(mod, 'Handlers'), modname), 'process')
        try:
            func(mlist, msg, msgdata)
        except DiscardMessage:
            # Throw the message away; we need do nothing else with it.
            return 0
        except MessageHeld:
            # Let the approval process take it from here.  The message no
            # longer needs to be queued.
            return 0
        except SomeRecipientsFailed:
            # The delivery module being used (SMTPDirect or Sendmail) failed
            # to deliver the message to one or all of the recipients.  Push
            # the delivery module back on the pipeline list and break.
            pipeline.insert(0, modname)
            # Consult and adjust some meager metrics that try to decide
            # whether it's worth continuing to attempt delivery of this
            # message.
            now = time.time()
            recips = msgdata['recips']
            last_recip_count = msgdata.get('last_recip_count', 0)
            deliver_until = msgdata.get('deliver_until', now)
            if len(recips) == last_recip_count:
                # We didn't make any progress.  How many times to we continue
                # to attempt delivery?  TBD: make this configurable.
                if now > deliver_until:
                    # throw this message away
                    return 0
            else:
                # Keep trying to delivery this for 3 days
                deliver_until = now + 60*60*24*3
            msgdata['last_recip_count'] = len(recips)
            msgdata['deliver_until'] = deliver_until
            break
        except Exception, e:
            # Some other exception occurred, which we definitely did not
            # expect, so set this message up for queuing.  This is mildly
            # offensive since we're doing the equivalent of a bare except,
            # which gobbles useful bug reporting.  Still, it's more important
            # that email not get lost, so we log the exception and the
            # traceback so that we have a hope of fixing this.  We may want to
            # email the site admin or (shudder) the Mailman maintainers.
            #
            # We stick the name of the failed module back into the front of
            # the pipeline list so that it can resume where it left off when
            # qrunner tries to redeliver it.
            pipeline.insert(0, modname)
            mlist.LogMsg('error', 'Delivery exception: %s' % e)
            s = StringIO()
            traceback.print_exc(file=s)
            mlist.LogMsg('error', s.getvalue())
            break
    msgdata['pipeline'] = pipeline
    if pipeline:
        msg.Enqueue(mlist, newdata=msgdata)
    # for cron qrunner
    return not not len(pipeline)



# For messages that qrunner tries to re-deliver using the pre 2.0beta3 qfiles
# data format.
def RedeliverMessage(mlist, msg):
    msgdata = {'pipeline': [mm_cfg.DELIVERY_MODULE]}
    return DeliverToList(mlist, msg, msgdata)



# for messages crafted internally by the Mailman system.  The msg object
# should have already calculated and set msg.recips.  TBD: can the mlist be
# None?
def DeliverToUser(mlist, msg, newdata={}):
    pipeline = ['Replybot',
                'CookHeaders',
                mm_cfg.DELIVERY_MODULE,
                ]
    msgdata = {'pipeline' : pipeline,
               'fasttrack': 1,
               }
    recips = getattr(msg, 'recips', None)
    if recips is not None:
        msgdata['recips'] = recips
    msgdata.update(newdata)
    return DeliverToList(mlist, msg, msgdata)
