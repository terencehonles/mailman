#! /usr/bin/env python
#
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

"""Process and produce the list-administration options forms.

To run stand-alone for debugging, set env var PATH_INFO to name of list
and, optionally, options category."""


import sys
import os, cgi, string, types, time
import paths                                      # path hacking
from Mailman import Utils, MailList, Errors, MailCommandHandler
from Mailman import Cookie
from Mailman.htmlformat import *
from Mailman.Crypt import crypt
from Mailman import mm_cfg

CATEGORIES = [('general', "General Options"),
              ('members', "Membership Management"),
              ('privacy', "Privacy Options"),
              ('nondigest', "Regular-member (non-digest) Options"),
              ('digest', "Digest-member Options"),
              ('bounce', "Bounce Options"),
              ('archive', "Archival Options"),
	      ('gateway', "Mail-News and News-Mail gateways")]



def isAuthenticated(list, password=None, SECRET="SECRET"):
    if password is not None:  # explicit login
        try:             
            list.ConfirmAdminPassword(password)
        except Errors.MMBadPasswordError:
            AddErrorMessage(doc, 'Error: Incorrect admin password.')
            return 0

        token = `hash(list_name)`
        c = Cookie.Cookie()
        cookie_key = list_name + "-admin"
        c[cookie_key] = token
        c[cookie_key]['expires'] = mm_cfg.ADMIN_COOKIE_LIFE
        print c                         # Output the cookie
        return 1
    if os.environ.has_key('HTTP_COOKIE'):
        c = Cookie.Cookie( os.environ['HTTP_COOKIE'] )
        if c.has_key(list_name + "-admin"):
	    if c[list_name + "-admin"].value == `hash(list_name)`:
		return 1
	    else:
		AddErrorMessage(doc, "error decoding authorization cookie")
		return 0
    return 0


def main():
    """Process and produce list options form.

    CGI input indicates that we're returning from submission of some new
    settings, which is processed before producing the new version."""
    global list_name, list_info, doc
    doc = Document()

    try:
        path = os.environ['PATH_INFO']
    except KeyError:
        path = ""
    list_info = Utils.GetPathPieces(path)
    # How many ../'s we need to get back to http://host/mailman

    if len(list_info) == 0:
        FormatAdminOverview()
	return

    list_name = string.lower(list_info[0])

    try: 
        lst = MailList.MailList(list_name)
    except Errors.MMUnknownListError:
        lst = None
    try:
	if not (lst and lst._ready):
            FormatAdminOverview(error="List <em>%s</em> not found."
                                % list_name)
            return

        if len(list_info) == 1:
            category = 'general'
            category_suffix = ''
        else:
            category = list_info[1]
            category_suffix = category

        if category not in map(lambda x: x[0], CATEGORIES):
            category = 'general'
        global cgi_data
        cgi_data = cgi.FieldStorage()
        is_auth = 0
        if cgi_data.has_key("adminpw"):
            is_auth = isAuthenticated(lst, cgi_data["adminpw"].value)
            message = FontAttr("Sorry, wrong password. Try again.",
                               color="ff5060", size="+1").Format()
        else: 
             is_auth = isAuthenticated(lst)
             message = ""
        if not is_auth:
            defaulturi = '/mailman/admin%s/%s' % (mm_cfg.CGIEXT, list_name)
            print "Content-type: text/html\n\n"
            text = Utils.maketext(
                'admlogin.txt',
                {"listname": list_name,
                 "path"    : Utils.GetRequestURI(defaulturi),
                 "message" : message,
                 })
            print text
            return
        
        # is the request for variable details?
        varhelp = None
        if cgi_data.has_key('VARHELP'):
            varhelp = cgi_data['VARHELP'].value
        elif cgi_data.has_key('request_login') and \
             os.environ.get('QUERY_STRING'):
            # POST methods, even if their actions have a query string, don't
            # get put into FieldStorage's keys :-(
            qs = cgi.parse_qs(os.environ['QUERY_STRING']).get('VARHELP')
            if qs and type(qs) == types.ListType:
                varhelp = qs[0]
        if varhelp:
            FormatOptionHelp(doc, varhelp, lst)
            print doc.Format(bgcolor="#ffffff")
            return

        if cgi_data.has_key('bounce_matching_headers'):
            try:
                pairs = lst.parse_matching_header_opt()
            except Errors.MMBadConfigError, line:
                AddErrorMessage(doc,
                                'Warning: bad matching-header line'
                                ' (does it have the colon?)<ul> %s </ul>',
                                line)

	if not lst.digestable and len(lst.GetDigestMembers()):
	    AddErrorMessage(doc,
                            'Warning:  you have digest members,'
                            ' but digests are turned off.'
                            '  Those people will not receive mail.')
	if not lst.nondigestable and len(lst.GetMembers()):
	    AddErrorMessage(doc,
                            'Warning:  you have lst members,'
                            ' but non-digestified mail is turned'
                            ' off.  They will receive mail until'
                            ' you fix this problem.')
        if len(cgi_data.keys()):
            ChangeOptions(lst, category, cgi_data, doc)
	FormatConfiguration(doc, lst, category, category_suffix)
	print doc.Format(bgcolor="#ffffff")

    finally:
        if lst:
  	    lst.Unlock()

# Form Production:

def FormatAdminOverview(error=None):
    "Present a general welcome and itemize the (public) lists."
    doc = Document()
    legend = "%s mailing lists - Admin Links" % mm_cfg.DEFAULT_HOST_NAME
    doc.SetTitle(legend)

    table = Table(border=0, width="100%")
    table.AddRow([Center(Header(2, legend))])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0,
                      colspan=2, bgcolor="#99ccff")

    advertised = []
    names = Utils.list_names()
    names.sort()
    for n in names:
	l = MailList.MailList(n, lock=0)
        if l.advertised: advertised.append(l)

    if error:
	greeting = FontAttr(error, color="ff5060", size="+1")
    else:
	greeting = "Welcome!"

    if not advertised:
        welcome_items = (greeting,
			 "<p>"
			 " There currently are no publicly-advertised ",
			 Link(mm_cfg.MAILMAN_URL, "mailman"),
			 " mailing lists on %s." % mm_cfg.DEFAULT_HOST_NAME,
			 )
    else:

        welcome_items = (
	    greeting,
            "<p>"
            " Below is the collection of publicly-advertised ",
            Link(mm_cfg.MAILMAN_URL, "mailman"),
            " mailing lists on %s." % mm_cfg.DEFAULT_HOST_NAME,
            (' Click on a list name to visit the configuration pages'
             ' for that list.'
             )
            )

    welcome_items = (welcome_items +
                     (" To visit the administrators configuration page for"
                      " an unadvertised list, open a URL similar to this"
                      +
                      (" one, but with a '/' and the %slist name appended.<p>"
                       % ((error and "the right ") or ""))
                      +
                      " General list information can be found at ",
                      Link("%slistinfo%s" % ('../' * Utils.GetNestingLevel(),
                                             mm_cfg.CGIEXT),
                           "the mailing list overview page"),
                      "."
                      "<p>(Send questions and comments to ",
                     Link("mailto:%s" % mm_cfg.MAILMAN_OWNER,
                          mm_cfg.MAILMAN_OWNER),
                     ".)<p>"
                      )
                     )

    table.AddRow([apply(Container, welcome_items)])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0, colspan=2)

    if advertised:
        table.AddRow([Italic("List"), Italic("Description")])
        for l in advertised:
            table.AddRow([Link(l.GetRelativeScriptURL('admin'), 
	                  Bold(l.real_name)),l.description])

    doc.AddItem(table)

    print doc.Format(bgcolor="#ffffff")

def FormatConfiguration(doc, lst, category, category_suffix):
    """Produce the overall doc, *except* any processing error messages."""
    for k, v in CATEGORIES:
        if k == category: label = v

    doc.SetTitle('%s Administration' % lst.real_name)
    doc.AddItem(Center(Header(2, ('%s Mailing list Configuration - %s Section'
                                  % (lst.real_name, label)))))
    doc.AddItem('<hr>')

    links_table = Table(valign="top")

    links_table.AddRow([Center(Bold("Configuration Categories")),
                        Center(Bold("Other Administrative Activities"))])
    other_links = UnorderedList()
    link = Link(lst.GetRelativeScriptURL('admindb'), 
                'Tend to pending administrative requests.')
    other_links.AddItem(link)
    link = Link(lst.GetRelativeScriptURL('listinfo'),
                'Go to the general list information page.')
    other_links.AddItem(link)
    link = Link(lst.GetRelativeScriptURL('edithtml'),
                'Edit the HTML for the public list pages.')
    other_links.AddItem(link)

    these_links = UnorderedList()
    for k, v in CATEGORIES:
        if k == category:
            these_links.AddItem("<b> =&gt; " + v + " &lt;= </b>")
        else:
            these_links.AddItem(Link("%s/%s" % 
	                 (lst.GetRelativeScriptURL('admin'),k),v))

    links_table.AddRow([these_links, other_links])
    links_table.AddRowInfo(max(links_table.GetCurrentRowIndex(), 0),
                           valign="top")

    doc.AddItem(links_table)
    doc.AddItem('<hr>')
    if category_suffix:
        form = Form("%s/%s" % (lst.GetRelativeScriptURL('admin'),
                                  category_suffix))
    else:
        form = Form(lst.GetRelativeScriptURL('admin'))
    doc.AddItem(form)

    form.AddItem("Make your changes below, and then submit them using the"
                 " bottom at the bottom.  (You can change your password"
                 " there, too.)<p>")

    form.AddItem(FormatOptionsSection(category, lst))

    if category == 'general':
        form.AddItem(Center(FormatPasswordStuff()))

    form.AddItem("<p>")

    form.AddItem(Center(FormatSubmit()))

    form.AddItem(lst.GetMailmanFooter())

def FormatOptionsSection(category, lst):
    """Produce the category-specific options table."""
    if category == 'members':
        # Special case for members section.
        return FormatMembershipOptions(lst)

    options = GetConfigOptions(lst, category)

    big_table = Table(cellspacing=3, cellpadding=4)

    # Get and portray the text label for the category.
    for k, v in CATEGORIES:
        if k == category: label = v
    big_table.AddRow([Center(Header(2, label))])
    big_table.AddCellInfo(max(big_table.GetCurrentRowIndex(), 0), 0,
                          colspan=2, bgcolor="#99ccff")

    def ColHeader(big_table = big_table):
        big_table.AddRow([Center(Bold('Description')), Center(Bold('Value'))])
        big_table.AddCellInfo(max(big_table.GetCurrentRowIndex(), 0), 0,
                              width="15%")
        big_table.AddCellInfo(max(big_table.GetCurrentRowIndex(), 0), 1,
                              width="85%")
    did_col_header = 0

    for item in options:
        if type(item) == types.StringType:
	    # The very first banner option (string in an options list) is
	    # treated as a general description, while any others are
	    # treated as section headers - centered and italicized...
	    if did_col_header:
		item = "<center><i>" + item + "</i></center>"
            big_table.AddRow([item])
	    big_table.AddCellInfo(max(big_table.GetCurrentRowIndex(), 0),
				  0, colspan=2)
            if not did_col_header:
                # Do col header after very first string descr, if any...
                ColHeader()
                did_col_header = 1
        else:
            if not did_col_header:
                # ... but do col header before anything else.
                ColHeader()
                did_col_header = 1
	    AddOptionsTableItem(big_table, item, category, lst)
    big_table.AddRow(['<br>'])
    big_table.AddCellInfo(big_table.GetCurrentRowIndex(), 0, colspan=2)
    return big_table

def AddOptionsTableItem(table, item, category, lst, nodetails=0):
    """Add a row to an options table with the item description and value."""
    try:
	got = GetItemCharacteristics(item)
	varname, kind, params, dependancies, descr, elaboration = got
    except ValueError, msg:
        lst.LogMsg("error", "admin: %s", msg)
        return Italic("<malformed option>")
    descr = GetItemGuiDescr(lst, category, varname, descr,
			    elaboration, nodetails)
    val = GetItemGuiValue(lst, kind, varname, params)
    table.AddRow([descr, val])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 1,
		      bgcolor="#cccccc")
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0,
		      bgcolor="#cccccc")

def FormatOptionHelp(doc, varref, lst):
    item = bad = None
    reflist = string.split(varref, '/')
    if len(reflist) == 2:
        category, varname = reflist
        options = GetConfigOptions(lst, category)
        for i in options:
            if i and i[0] == varname:
                item = i
                break
    if not item:
	bad = ("Option %s/%s not found. %s"
	       % (category, varname, os.environ['PATH_INFO']))
    else:
	try:
	    got = GetItemCharacteristics(item)
	    varname, kind, params, dependancies, descr, elaboration = got
	except ValueError, msg:
	    bad = msg
    if not bad and not elaboration:
        bad = "Option %s has no extended help." % varname
    if bad:
	AddErrorMessage(doc, bad)
	return

    header = Table(width="100%")
    legend = ('%s Mailing list Configuration Help<br><em>%s</em> Option'
	      % (lst.real_name, varname))
    header.AddRow([Center(Header(3, legend))])
    header.AddCellInfo(max(header.GetCurrentRowIndex(), 0), 0,
                       colspan=2, bgcolor="#99ccff")
    doc.SetTitle("Mailman %s List Option Help" % varname)
    doc.AddItem(header)
    doc.AddItem("<b>%s</b> (%s): %s<p>" % (varname, category, item[4]))
    doc.AddItem("%s<p>" % item[5])

    form = Form("%s/%s" % (lst.GetRelativeScriptURL('admin'), category))
    valtab = Table(cellspacing=3, cellpadding=4)
    AddOptionsTableItem(valtab, item, category, lst, nodetails=1)
    form.AddItem(valtab)
    # XXX I don't think we want to be able to set options from two places,
    #     since they'll go out of sync.
    #form.AddItem(Center(FormatPasswordStuff()))
    doc.AddItem(Center(form))

def GetItemCharacteristics(table_entry):
    """Break out the components of an item description from its table entry:
      0 option-var name
      1 type
      2 entry size
      3 ?dependancies?
      4 Brief description
      5 Optional description elaboration"""    
    if len(table_entry) == 5:
        elaboration = None
        varname, kind, params, dependancies, descr = table_entry
    elif len(table_entry) == 6:
        varname, kind, params, dependancies, descr, elaboration = table_entry
    else:
	raise ValueError, ("Badly formed options entry:\n  %s"
			   % table_entry)
    return (varname, kind, params, dependancies, descr, elaboration)

def GetItemGuiValue(lst, kind, varname, params):
    """Return a representation of an item's settings."""
    if kind == mm_cfg.Radio or kind == mm_cfg.Toggle:
        #
        # if we are sending returning the option for subscribe
        # policy and this site doesn't allow open subscribes,
        # then we have to alter the value of lst.subscribe_policy
        # as passed to RadioButtonArray in order to compensate
        # for the fact that there is one fewer option. correspondingly,
        # we alter the value back in the change options function -scott
        #
        if varname == "subscribe_policy" and not mm_cfg.ALLOW_OPEN_SUBSCRIBE:
            return RadioButtonArray(varname, params, getattr(lst, varname) - 1)
        else:
            return RadioButtonArray(varname, params, getattr(lst, varname))
    elif (kind == mm_cfg.String or kind == mm_cfg.Email or
	  kind == mm_cfg.Host or kind == mm_cfg.Number):
	return TextBox(varname, getattr(lst, varname), params)
    elif kind == mm_cfg.Text:
	if params:
	    r, c = params
	else:
	    r, c = None, None
	val = getattr(lst, varname)
	if not val:
	    val = ''
	return TextArea(varname, val, r, c)
    elif kind == mm_cfg.EmailList:
	if params:
	    r, c = params
	else:
	    r, c = None, None
	res = string.join(getattr(lst, varname), '\n')
	return TextArea(varname, res, r, c, wrap='off')
    
def GetItemGuiDescr(lst, category, varname, descr, elaboration, nodetails):
    """Return a representation of an item's description, with link to
    elaboration if any."""
    descr = '<div ALIGN="right">' + descr
    if not nodetails and elaboration:
        ref = "../" * (Utils.GetNestingLevel()-1) + list_name + "/"
        ref = ref + '?VARHELP=' + category + "/" + varname
        descr = Container(descr,
			  Link(ref, " (Details)", target="MMHelp"),
			  "</div>")
    else:
        descr = descr + "</div>"
    return descr

def FormatMembershipOptions(lst):
    container = Container()
    header = Table(width="100%")
    header.AddRow([Center(Header(2, "Membership Management"))])
    header.AddCellInfo(max(header.GetCurrentRowIndex(), 0), 0,
                       colspan=2, bgcolor="#99ccff")
    container.AddItem(header)
    user_table = Table(width="90%", border='2')
    user_table.AddRow([Center(Header(4, "Membership List"))])
    user_table.AddCellInfo(user_table.GetCurrentRowIndex(),
                           user_table.GetCurrentCellIndex(),
                           bgcolor="#cccccc", colspan=8)
    user_table.AddRow(
        [Center(Italic("(%s members total, max. %s at a time displayed)" %
                       (len(lst.members)
                        + len(lst.digest_members),
                        lst.admin_member_chunksize)))])
    user_table.AddCellInfo(user_table.GetCurrentRowIndex(),
                           user_table.GetCurrentCellIndex(),
                           bgcolor="#cccccc", colspan=8)

    user_table.AddRow(map(Center, ['member address', 'subscr', 'digest',
                                   'hide', 'nomail', 'ack', 'norcv',
                                   'plain']))
    rowindex = user_table.GetCurrentRowIndex()
    for i in range(8):
        user_table.AddCellInfo(rowindex, i, bgcolor='#cccccc')
    all = lst.GetMembers() + lst.GetDigestMembers()
    if len(all) > lst.admin_member_chunksize:
        chunks = Utils.chunkify(all, lst.admin_member_chunksize)
        if not cgi_data.has_key("chunk"):
            chunk = 0
        else:
            chunk = string.atoi(cgi_data["chunk"].value)
        all = chunks[chunk]
        footer = ("<p><em>To View other sections, "
                  "click on the appropriate range listed below</em>")
        chunk_indices = range(len(chunks))
        chunk_indices.remove(chunk)
        buttons = []
        for ci in chunk_indices:
            start, end = chunks[ci][0], chunks[ci][-1]
	    url = lst.GetAbsoluteScriptURL('admin')
            buttons.append("<a href=%s/members?chunk=%d> from %s to %s </a>"
                           % ( url,  ci, start, end))
        buttons = apply(UnorderedList, tuple(buttons))
        footer = footer + buttons.Format() + "<p>"
    else:
        all.sort()
        footer = "<p>"
    for member in all:
        cells = [member + "<input type=hidden name=user value=%s>" % (member),
                 CheckBox(member + "_subscribed", "on", 1).Format()]
        if lst.members.has_key(member):
            cells.append(CheckBox(member + "_digest", "off", 0).Format())
        else:
            cells.append(CheckBox(member + "_digest", "on", 1).Format())
        for opt in ("hide", "nomail", "ack", "norcv", "plain"):
            if lst.GetUserOption(member, MailCommandHandler.option_info[opt]):
                value = "on"
                checked = 1
            else:
                value = "off"
                checked = 0
            box = CheckBox("%s_%s" % (member, opt), value, checked)
            cells.append(box.Format())
        user_table.AddRow(cells)
    container.AddItem(Center(user_table))
    legend = UnorderedList()
    legend.AddItem('<b>subscr</b> -- Is the member subscribed?')
    legend.AddItem('<b>digest</b> -- '
                   'Does the member get messages in digests? '
                   '(otherwise, individual messages)')
    legend.AddItem('<b>hide</b> -- '
                   "Is the member's address hidden from Web browsers?")
    legend.AddItem('<b>nomail</b> -- Is delivery to the member disabled?')
    legend.AddItem('<b>ack</b> -- '
                   'Does the member get acknowledgements of their posts?')
    legend.AddItem('<b>norcv</b> -- '
                   'Does the member get copies of their own posts?')
    legend.AddItem(
        '<b>plain</b> -- '
        'If getting digests, does the member get plain text digests? '
        '(otherwise, MIME)')
    container.AddItem(legend.Format())
    container.AddItem(footer)
    t = Table(width="90%")
    t.AddRow([Center(Header(4, "Mass Subscribe Members"))])
    t.AddCellInfo(t.GetCurrentRowIndex(),
                  t.GetCurrentCellIndex(),
                  bgcolor="#cccccc", colspan=8)
    if lst.send_welcome_msg:
        nochecked = 0
        yeschecked = 1
    else:
        nochecked = 1
        yeschecked = 0
    t.AddRow([("<b>1.</b> Send Welcome message to this batch? "
               + RadioButton("send_welcome_msg_to_this_batch", 0,
                             nochecked).Format()
               + " no "
               + RadioButton("send_welcome_msg_to_this_batch", 1,
                             yeschecked).Format()
               + " yes ")])
    t.AddRow(["<b>2.</b> Enter one address per line: <p>"])
    container.AddItem(Center(t))
    container.AddItem(Center(TextArea(name='subscribees',
                                      rows=10,cols=60,wrap=None)))
    return container

def FormatPasswordStuff():
    change_pw_table = Table(bgcolor="#99cccc", border=0,
                            cellspacing=0, cellpadding=2,
                            valign="top")
    change_pw_table.AddRow(
        [Bold(Center('To Change The Administrator Password'))])
    change_pw_table.AddCellInfo(0, 0, align="left", colspan=2)
    old = Table(bgcolor="#99cccc", border=1,
                cellspacing=0, cellpadding=2, valign="top")
    old.AddRow(['<div ALIGN="right"> Enter current password:</div>',
                PasswordBox('adminpw')])
    new = Table(bgcolor="#99cccc", border=1,
                cellspacing=0, cellpadding=2, valign="top")
    new.AddRow(['<div ALIGN="right"> Enter new password: </div>',
                PasswordBox('newpw')])
    new.AddRow(['<div ALIGN="right">Confirm new password:</div>',
                PasswordBox('confirmpw')])
    change_pw_table.AddRow([old, new])
    change_pw_table.AddCellInfo(1, 0, align="left", valign="top")
    #change_pw_table.AddCellInfo(1, 1, align="left", valign="top")
    return change_pw_table

def FormatSubmit():
    submit = Table(bgcolor="#99ccff",
                   border=0, cellspacing=0, cellpadding=2)
    submit.AddRow([Bold(SubmitButton('submit', 'Submit Your Changes'))])
    submit.AddCellInfo(submit.GetCurrentRowIndex(), 0, align="middle")
    return submit

# XXX klm - looks like turn_on_moderation is orphaned.
turn_on_moderation = 0

# Options processing

def GetValidValue(lst, prop, my_type, val, dependant):
    if my_type == mm_cfg.Radio or my_type == mm_cfg.Toggle:
	if type(val) <> types.IntType:
            try:
                val = int(val)
            except ValueError:
		pass
		# Don't know what to do here...
	    return val
    elif my_type == mm_cfg.String or my_type == mm_cfg.Text:
	return val
    elif my_type == mm_cfg.Email:
	try:
            Utils.ValidateEmail(val)
            return val
        except Errors.EmailAddressError:
            pass
	# Revert to the old value.
	return getattr(lst, prop)
    elif my_type == mm_cfg.EmailList:
	def SafeValidAddr(addr):
	    try:
                Utils.ValidateEmail(addr)
                return 1
            except Errors.EmailAddressError:
                return 0

	val = filter(SafeValidAddr,
		     map(string.strip, string.split(val, '\n')))
	if dependant and len(val):
	    # Wait till we've set everything to turn it on,
	    # as we don't want to clobber our special case.
	    # XXX klm - looks like turn_on_moderation is orphaned?
	    turn_on_moderation = 1
	return val
    elif my_type == mm_cfg.Host:
	return val
##
##      This code is sendmail dependant, so we'll just live w/o 
##      the error checking for now.
##
## 	# Shouldn't have to read in the whole file.
## 	file = open('/etc/sendmail.cf', 'r')
## 	lines = string.split(file.read(), '\n')
## 	file.close()
## 	def ConfirmCWEntry(item):
## 	    return item[0:2] == 'Cw'
## 	lines = filter(ConfirmCWEntry, lines)
## 	if not len(lines):
## 	    # Revert to the old value.
## 	    return getattr(list, prop)
## 	for line in lines:
## 	    if string.lower(string.strip(line[2:])) == string.lower(val):
## 		return val
## 	return getattr(list, prop)
    elif my_type == mm_cfg.Number:
        num = -1
        try:
            num = int(val)
        except ValueError:
            # TBD: a float???
            try:
                num = float(val)
            except ValueError:
                pass
        if num < 0:
            return getattr(lst, prop)
        return num
    else:
	# Should never get here...
	return val


def ChangeOptions(lst, category, cgi_info, document):
    dirty = 0
    confirmed = 0
    if cgi_info.has_key('newpw'):
	if cgi_info.has_key('confirmpw'):
            if cgi_info.has_key('adminpw'):
                try:
                    lst.ConfirmAdminPassword(cgi_info['adminpw'].value)
                    confirmed = 1
                except Errors.MMBadPasswordError:
                    m = "Error: incorrect administrator password"
                    document.AddItem(Header(3, Italic(FontAttr(m, color="ff5060"))))
                    confirmed = 0
            if confirmed:
                new = cgi_info['newpw'].value
                confirm = cgi_info['confirmpw'].value
                if new == confirm:
                    lst.password = crypt(new, Utils.GetRandomSeed())
                    dirty = 1
                else:
                    m = 'Error: Passwords did not match.'
                    document.AddItem(Header(3, Italic(FontAttr(m, color="ff5060"))))

	else:
	    m = 'Error: You must type in your new password twice.'
	    document.AddItem(
                Header(3, Italic(FontAttr(m, color="ff5060"))))
    #
    # for some reason, the login page mangles important values for the list
    # such as .real_name so we only process these changes if the category
    # is not "members" and the request is not from the login page
    # -scott 19980515
    #
    if category != 'members' and not cgi_info.has_key("request_login") and\
       len(cgi_info.keys()) > 1:
        if cgi_info.has_key("subscribe_policy"):
            if not mm_cfg.ALLOW_OPEN_SUBSCRIBE:
                #
                # we have to add one to the value because the
                # page didn't present an open list as an option
                #
                page_setting = string.atoi(cgi_info["subscribe_policy"].value)
                cgi_info["subscribe_policy"].value = str(page_setting + 1)

        opt_list = GetConfigOptions(lst, category)
        for item in opt_list:
            if len(item) < 5:
                continue
            property, kind, args, deps, desc = (item[0], item[1], item[2],
                                                item[3], item[4])
            if not cgi_info.has_key(property):
                if (kind <> mm_cfg.Text and 
                    kind <> mm_cfg.String and 
                    kind <> mm_cfg.EmailList):
                    continue
                else:
                    val = ''
            else:
                val = cgi_info[property].value
            value = GetValidValue(lst, property, kind, val, deps)
            if getattr(lst, property) != value:
                setattr(lst, property, value)
                dirty = 1
    #
    # mass subscription processing for members category
    #
    if cgi_info.has_key('subscribees'):
	name_text = cgi_info['subscribees'].value
        name_text = string.replace(name_text, '\r', '')
	names = string.split(name_text, '\n')
        subscribe_success = []
        subscribe_errors = []
        send_welcome_msg = string.atoi(
            cgi_info["send_welcome_msg_to_this_batch"].value)
	for new_name in map(string.strip, names):
            new_name = Utils.ParseAddrs(new_name)
            digest = 0
            if not lst.digestable:
                digest = 0
            if not lst.nondigestable:
                digest = 1
	    try:
                Utils.ValidateEmail(new_name)
		lst.ApprovedAddMember(
                    new_name,
                    Utils.GetRandomSeed() + Utils.GetRandomSeed(),
                    digest, send_welcome_msg)
                subscribe_success.append(new_name)
	    except Errors.MMAlreadyAMember:
                subscribe_errors.append((new_name, 'Already a member'))
            except Errors.MMBadEmailError:
                if new_name == '':
                    new_name = '&lt;blank line&gt;'
                subscribe_errors.append(
                    (new_name, "Bad/Invalid email address"))
            except Errors.MMHostileAddress:
                subscribe_errors.append(
                    (new_name, "Hostile Address (illegal characters)"))
        if subscribe_success:
            document.AddItem(Header(5, "Successfully Subscribed:"))
            document.AddItem(apply(UnorderedList, tuple((subscribe_success))))
            document.AddItem("<p>")
            dirty = 1
        if subscribe_errors:
            document.AddItem(Header(5, "Error Subscribing:"))
            items = map(lambda x: "%s -- %s" % (x[0], x[1]), subscribe_errors)
            document.AddItem(apply(UnorderedList, tuple((items))))
            document.AddItem("<p>")
    #
    # do the user options for members category
    #
    if cgi_info.has_key('user'):
        user = cgi_info["user"]
        if type(user) is type([]):
            users = []
            for ui in range(len(user)):
                users.append(user[ui].value)
        else:
            users = [user.value]
        for user in users:
            if not cgi_info.has_key('%s_subscribed' % (user)):
                lst.DeleteMember(user)
                dirty = 1
                continue
            if not cgi_info.has_key("%s_digest" % (user)):
                if lst.digest_members.has_key(user):
                    del lst.digest_members[user]
                    dirty = 1
                if not lst.members.has_key(user):
                    lst.members[user] = 0
                    dirty = 1
            else:
                if not lst.digest_members.has_key(user):
                    lst.digest_members[user] = 0
                    dirty = 1
                if lst.members.has_key(user):
                    del lst.members[user]
                    dirty = 1
                
            for opt in ("hide", "nomail", "ack", "norcv", "plain"):
                if cgi_info.has_key("%s_%s" % (user, opt)):
                    lst.SetUserOption(user, MailCommandHandler.option_info[opt], 1)
                    dirty = 1
                else:
                    lst.SetUserOption(user, MailCommandHandler.option_info[opt], 0)
                    dirty = 1


    if dirty:
        lst.Save()

def AddErrorMessage(doc, errmsg, *args):
    doc.AddItem(Header(3, Italic(FontAttr(errmsg % args,
                                          color="#ff66cc"))))


_config_info = None
def GetConfigOptions(lst, category):
    global _config_info
    if _config_info == None:
        _config_info = lst.GetConfigInfo()
    return _config_info[category]

