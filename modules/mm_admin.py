# When an operation can't be completed, and is sent to the list admin for
# Handling, we consider that an error condition, and raise MMNeedApproval

import mm_err, mm_cfg, mm_message
import os, marshal, time, string

SUBSCRIPTION_AUTH_TEXT = """
Your authorization is required for a maillist subscription request approval:

For:		%s
List:		%s@%s

At your convenience, visit:

	%s
	
to process the request."""

POSTING_AUTH_TEXT = """
Your authorization is required for a maillist posting request approval:

List:		%s@%s
Reason held:	%s
From:		%s
Subject:	%s

At your convenience, visit:

	%s
	
to approve or deny the request."""

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
		self.SendTextToUser(subject = subj,
				    recipient = self.GetAdminEmail(),
				    text = (SUBSCRIPTION_AUTH_TEXT
					    % (who,
					       self.real_name,
					       self.host_name,
					       self.GetScriptURL('admindb'))))
	    raise mm_err.MMNeedApproval, "Admin approval required to subscribe"

	elif request == 'post':
	    sender = args[0][0]
	    reason = args[1]
	    subject = args[2]
	    self.LogMsg("vette",
			("%s: %s post hold, %s"
			 % (self.real_name, sender, `reason`)))
	    if self.admin_immed_notify:
		subj = '%s post approval required for %s' % (self.real_name,
							     sender)
		self.SendTextToUser(subject = subj,
				    recipient = self.GetAdminEmail(),
				    text = (POSTING_AUTH_TEXT
					    % (self.real_name,
					       self.host_name,
					       reason,
					       sender,
					       subject,
					       self.GetScriptURL('admindb'))))
	    raise mm_err.MMNeedApproval, args[1]

    def CleanRequests(self):
	for (key, val) in self.requests.items():
	    if not len(val):
		del self.requests[key]

    def GetRequest(self, id):
	for (key, val) in self.requests.items():
	    for i in range(len(val)):
		if val[i][0] == id:
		    return (key, i)
	raise mm_err.MMBadRequestId

    def RemoveRequest(self, id):
	for (key, val) in self.requests.items():
	    for item in val:
		if item[0] == id:
		    val.remove(item)
		    return
	raise mm_err.MMBadRequestId

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
	msg = mm_message.IncomingMessage(data[0][1])
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
	    except mm_err.MMAlreadyAMember:
		pass



# Don't call any methods below this point from outside this mixin.

    def GetRequestId(self):
	id = self.next_request_id
	self.next_request_id = self.next_request_id + 1
	# No need to save, we know it's about to be done.
	return id

    def RefuseRequest(self, request, destination_email, comment, msg=None):
	text = '''Your request to the '%s' mailing-list:

	%s

Has been rejected by the list moderator.
''' % (self.real_name, request)
        if comment:
	    text = text + '''
The moderator gave the following reason for rejecting your request:

        %s

''' % comment
        text = text + 'Any questions or comments should be directed to %s.\n' \
	       % self.GetAdminEmail()
        if msg:
	    text = text  + '''
Your original message follows:

%s

%s
''' % (string.join(msg.headers, ''), msg.body)
	
        self.SendTextToUser(subject = '%s request rejected' % self.real_name,
                            recipient = destination_email,
			    text = text)

