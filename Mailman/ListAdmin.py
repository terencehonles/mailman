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


"""Mixin class which handles of administrative requests."""


# When an operation can't be completed, and is sent to the list admin for
# Handling, we consider that an error condition, and raise MMNeedApproval

import os
import marshal
import time
import string
import Errors
import Message
import Utils


class ListAdmin:
    def InitVars(self):
	# Non-configurable data:
	self.requests = {}
	self.next_request_id = 1

    def AddRequest(self, request, *args):
	now = time.time()
	request_id = self.GetRequestId()
	if not self.requests.has_key(request):
	    self.requests[request] = [(request_id, now) + args]
	else:
	    self.requests[request].append( (request_id, now) + args )
	self.Save()
	if request == 'add_member':
	    who = args[1]
	    self.LogMsg("vette", ("%s: Subscribe request: %s"
				  % (self.real_name, who)))
	    if self.admin_immed_notify:
		subj = 'New %s subscription request: %s' % (self.real_name,
							    who)
                text = Utils.maketext(
                    'subauth.txt',
                    {'username'   : who,
                     'listname'   : self.real_name,
                     'hostname'   : self.host_name,
                     'admindb_url': self.GetAbsoluteScriptURL('admindb'),
                     })
		self.SendTextToUser(subject = subj,
				    recipient = self.GetAdminEmail(),
				    text = text)
	    raise Errors.MMNeedApproval, "Admin approval required to subscribe"

	elif request == 'post':
	    sender = args[0][0]
	    reason = args[1]
	    subject = args[2]
	    self.LogMsg("vette", ("%s: %s post hold\n\t%s"
				  % (self.real_name, sender, `reason`)))
	    if self.admin_immed_notify:
		subj = '%s post approval required for %s' % (self.real_name,
							     sender)
                text = Utils.maketext(
                    'postauth.txt',
                    {'listname'   : self.real_name,
                     'hostname'   : self.host_name,
                     'reason'     : reason,
                     'sender'     : sender,
                     'subject'    : subject,
                     'admindb_url': self.GetAbsoluteScriptURL('admindb'),
                     })
		self.SendTextToUser(subject = subj,
				    recipient = self.GetAdminEmail(),
				    text = text)
	    raise Errors.MMNeedApproval, args[1]

    def CleanRequests(self):
	for (key, val) in self.requests.items():
	    if not len(val):
		del self.requests[key]

    def GetRequest(self, id):
	for (key, val) in self.requests.items():
	    for i in range(len(val)):
		if val[i][0] == id:
		    return (key, i)
	raise Errors.MMBadRequestId

    def RemoveRequest(self, id):
	for (key, val) in self.requests.items():
	    for item in val:
		if item[0] == id:
		    val.remove(item)
		    return
	raise Errors.MMBadRequestId

    def RequestsPending(self):
	self.CleanRequests()
	total = 0
	for (k,v) in self.requests.items():
	    total = total + len(v)
	return total

    def HandleRequest(self, request_info, value, comment=None):
	request = request_info[0]
	index = request_info[1]
	request_data = self.requests[request][index]
	if request == 'add_member':
	    self.HandleAddMemberRequest(request_data[2:], value, comment)
	elif request == 'post':
	    self.HandlePostRequest(request_data[2:], value, comment)
	self.RemoveRequest(request_data[0])

    def HandlePostRequest(self, data, value, comment):
	destination_email = data[0][0]
	msg = Message.IncomingMessage(data[0][1])
	rejection = None
	if not value:
            # Accept.
	    self.Post(msg, 1)
	    return
        elif value == 1:
            # Reject.
	    rejection = "Refused"
            subj = msg.getheader('subject')
            if subj == None:
                request = 'Posting of your untitled message'
            else:
                request = ('Posting of your message entitled:\n\t\t %s'
                           % subj)
	    if not comment:
		comment = data[1]
	    if not self.dont_respond_to_post_requests:
		self.RefuseRequest(request, destination_email,
				   comment, msg)
	else:
            # Discard.
	    rejection = "Discarded"
	if rejection:
	    note = "%s: %s posting:" % (self._internal_name, rejection)
	    note = note + "\n\tFrom: %s" % msg.GetSender()
	    note = note + ("\n\tSubject: %s"
			   % (msg.getheader('subject') or '<none>'))
	    if data[1]:
		note = note + "\n\tHeld: %s" % data[1]
	    if comment:
		note = note + "\n\tDiscarded: %s" % comment
            self.LogMsg("vette", note)

    def HandleAddMemberRequest(self, data, value, comment):
	digest = data[0]
	destination_email = data[1]
	pw = data[2]
	if value == 0:
	    if digest:
		digest_text = 'digest'
	    else:
		digest_text = 'nodigest'
	    self.RefuseRequest('subscribe %s %s' % (pw, digest_text),
			       destination_email, comment)
	else:
	    try:
		self.ApprovedAddMember(destination_email, pw, digest)
	    except Errors.MMAlreadyAMember:
		pass



# Don't call any methods below this point from outside this mixin.

    def GetRequestId(self):
	id = self.next_request_id
	self.next_request_id = self.next_request_id + 1
	# No need to save, we know it's about to be done.
	return id

    def RefuseRequest(self, request, destination_email, comment, msg=None):
        text = Utils.maketext(
            'refuse.txt',
            {'listname' : self.real_name,
             'request'  : request,
             'reason'   : comment or '[No reason given]',
             'adminaddr': self.GetAdminEmail(),
             })
        # add in original message, but not wrap/filled
        if msg:
            text = text + string.join(msg.headers, '') + '\n\n' + msg.body
        else:
            text = text + '[Original message unavailable]'
        # send it
        self.SendTextToUser(subject = '%s request rejected' % self.real_name,
                            recipient = destination_email,
			    text = text)
