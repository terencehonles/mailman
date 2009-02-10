# Copyright (C) 2002-2009 by the Free Software Foundation, Inc.
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

"""Maildir pre-queue runner.

Most MTAs can be configured to deliver messages to a `Maildir'[1].  This
runner will read messages from a maildir's new/ directory and inject them into
Mailman's qfiles/in directory for processing in the normal pipeline.  This
delivery mechanism contrasts with mail program delivery, where incoming
messages end up in qfiles/in via the MTA executing the scripts/post script
(and likewise for the other -aliases for each mailing list).

The advantage to Maildir delivery is that it is more efficient; there's no
need to fork an intervening program just to take the message from the MTA's
standard output, to the qfiles/in directory.

[1] http://cr.yp.to/proto/maildir.html

We're going to use the :info flag == 1, experimental status flag for our own
purposes.  The :1 can be followed by one of these letters:

- P means that MaildirRunner's in the process of parsing and enqueuing the
  message.  If successful, it will delete the file.

- X means something failed during the parse/enqueue phase.  An error message
  will be logged to log/error and the file will be renamed <filename>:1,X.
  MaildirRunner will never automatically return to this file, but once the
  problem is fixed, you can manually move the file back to the new/ directory
  and MaildirRunner will attempt to re-process it.  At some point we may do
  this automatically.

See the variable USE_MAILDIR in Defaults.py.in for enabling this delivery
mechanism.
"""

# NOTE: Maildir delivery is experimental in Mailman 2.1.

import os
import errno
import logging

from email.Parser import Parser
from email.Utils import parseaddr

from mailman.config import config
from mailman.message import Message
from mailman.queue import Runner

log = logging.getLogger('mailman.error')

# We only care about the listname and the subq as in listname@ or
# listname-request@
subqnames = ('admin', 'bounces', 'confirm', 'join', 'leave',
             'owner', 'request', 'subscribe', 'unsubscribe')

def getlistq(address):
    localpart, domain = address.split('@', 1)
    # TK: FIXME I only know configs of Postfix.
    if config.POSTFIX_STYLE_VIRTUAL_DOMAINS:
        p = localpart.split(config.POSTFIX_VIRTUAL_SEPARATOR, 1)
        if len(p) == 2:
            localpart, domain = p
    l = localpart.split('-')
    if l[-1] in subqnames:
        listname = '-'.join(l[:-1])
        subq = l[-1]
    else:
        listname = localpart
        subq = None
    return listname, subq, domain


class MaildirRunner(Runner):
    # This class is much different than most runners because it pulls files
    # of a different format than what scripts/post and friends leaves.  The
    # files this runner reads are just single message files as dropped into
    # the directory by the MTA.  This runner will read the file, and enqueue
    # it in the expected qfiles directory for normal processing.
    def __init__(self, slice=None, numslices=1):
        # Don't call the base class constructor, but build enough of the
        # underlying attributes to use the base class's implementation.
        self._stop = 0
        self._dir = os.path.join(config.MAILDIR_DIR, 'new')
        self._cur = os.path.join(config.MAILDIR_DIR, 'cur')
        self._parser = Parser(Message)

    def _one_iteration(self):
        # Refresh this each time through the list.
        listnames = list(config.list_manager.names)
        # Cruise through all the files currently in the new/ directory
        try:
            files = os.listdir(self._dir)
        except OSError, e:
            if e.errno <> errno.ENOENT:
                raise
            # Nothing's been delivered yet
            return 0
        for file in files:
            srcname = os.path.join(self._dir, file)
            dstname = os.path.join(self._cur, file + ':1,P')
            xdstname = os.path.join(self._cur, file + ':1,X')
            try:
                os.rename(srcname, dstname)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    # Some other MaildirRunner beat us to it
                    continue
                log.error('Could not rename maildir file: %s', srcname)
                raise
            # Now open, read, parse, and enqueue this message
            try:
                fp = open(dstname)
                try:
                    msg = self._parser.parse(fp)
                finally:
                    fp.close()
                # Now we need to figure out which queue of which list this
                # message was destined for.  See verp_bounce() in
                # BounceRunner.py for why we do things this way.
                vals = []
                for header in ('delivered-to', 'envelope-to', 'apparently-to'):
                    vals.extend(msg.get_all(header, []))
                for field in vals:
                    to = parseaddr(field)[1].lower()
                    if not to:
                        continue
                    listname, subq, domain = getlistq(to)
                    listname = listname + '@' + domain
                    if listname in listnames:
                        break
                else:
                    # As far as we can tell, this message isn't destined for
                    # any list on the system.  What to do?
                    log.error('Message apparently not for any list: %s',
                              xdstname)
                    os.rename(dstname, xdstname)
                    continue
                # BAW: blech, hardcoded
                msgdata = {'listname': listname}
                # -admin is deprecated
                if subq in ('bounces', 'admin'):
                    queue = Switchboard(config.BOUNCEQUEUE_DIR)
                elif subq == 'confirm':
                    msgdata['toconfirm'] = 1
                    queue = Switchboard(config.CMDQUEUE_DIR)
                elif subq in ('join', 'subscribe'):
                    msgdata['tojoin'] = 1
                    queue = Switchboard(config.CMDQUEUE_DIR)
                elif subq in ('leave', 'unsubscribe'):
                    msgdata['toleave'] = 1
                    queue = Switchboard(config.CMDQUEUE_DIR)
                elif subq == 'owner':
                    msgdata.update({
                        'toowner': True,
                        'envsender': config.SITE_OWNER_ADDRESS,
                        'pipeline': config.OWNER_PIPELINE,
                        })
                    queue = Switchboard(config.INQUEUE_DIR)
                elif subq is None:
                    msgdata['tolist'] = 1
                    queue = Switchboard(config.INQUEUE_DIR)
                elif subq == 'request':
                    msgdata['torequest'] = 1
                    queue = Switchboard(config.CMDQUEUE_DIR)
                else:
                    log.error('Unknown sub-queue: %s', subq)
                    os.rename(dstname, xdstname)
                    continue
                queue.enqueue(msg, msgdata)
                os.unlink(dstname)
            except Exception, e:
                os.rename(dstname, xdstname)
                log.error('%s', e)

    def _clean_up(self):
        pass
