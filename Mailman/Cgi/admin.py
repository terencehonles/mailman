# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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

"""

import os
import re
import cgi
import types
import sha
import urllib
from string import lowercase, digits

from mimelib.address import unquote

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman import MailCommandHandler
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Cgi import Auth
from Mailman.Logging.Syslog import syslog

# Mark, but don't translate yet
def _(s): return s

CATEGORIES = [('general',   _('General Options')),
              ('members',   _('Membership Management')),
              ('privacy',   _('Privacy Options')),
              ('nondigest', _('Regular-member (non-digest) Options')),
              ('digest',    _('Digest-member Options')),
              ('bounce',    _('Bounce Options')),
              ('archive',   _('Archival Options')),
              ('gateway',   _('Mail-News and News-Mail gateways')),
              ('autoreply', _('Auto-responder')),
              ]


# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

NL = '\n'



def main():
    global CATEGORIES

    # Try to find out which list is being administered
    parts = Utils.GetPathPieces()
    if not parts:
        # None, so just do the admin overview and be done with it
        admin_overview()
        return
    # Get the list object
    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        admin_overview(_('No such list <em>%(listname)s</em>'))
        syslog('error', 'Someone tried to access the admin interface for a '
               'non-existent list: %s' % listname)
        return
    #
    # Now that we know what list has been requested, all subsequent admin
    # pages are shown in that list's preferred language.
    i18n.set_language(mlist.preferred_language)
    # If the user is not authenticated, we're done.
    cgidata = cgi.FieldStorage(keep_blank_values=1)
    try:
        Auth.authenticate(mlist, cgidata)
    except Auth.NotLoggedInError, e:
        Auth.loginpage(mlist, 'admin', e.message)
        return
    # Which subcategory was requested?  Default is `general'
    if len(parts) == 1:
        category = 'general'
        category_suffix = ''
    else:
        category = parts[1]
        category_suffix = category
    # Is this a log-out request?
    if category == 'logout':
        print mlist.ZapCookie('admin')
        Auth.loginpage(mlist, 'admin', frontpage=1)
        return
    # Sanity check
    if category not in [x[0] for x in CATEGORIES]:
        category = 'general'
    # Is the request for variable details?
    varhelp = None
    if cgidata.has_key('VARHELP'):
        varhelp = cgidata['VARHELP'].value
    elif cgidata.has_key('request_login') and os.environ.get('QUERY_STRING'):
        # POST methods, even if their actions have a query string, don't get
        # put into FieldStorage's keys :-(
        qs = cgi.parse_qs(os.environ['QUERY_STRING']).get('VARHELP')
        if qs and type(qs) == types.ListType:
            varhelp = qs[0]
    if varhelp:
        option_help(mlist, varhelp)
        return
    # The html page document
    doc = Document()
    doc.set_language(mlist.preferred_language)
    # Now we're ready to do normal form processing.  For this, though we must
    # lock the mailing list, and everything from here on out must be wrapped
    # in a try/except.
    #
    # BAW: Currently we attempt to acquire the lock with no timeout, although
    # this could get hit by a webserver or client timeout, if there's a long
    # or stale lock on the list.  Maybe we should have a configurable timeout
    # setting after which we'll just inform the user that the operation
    # couldn't be performed?
    mlist.Lock()
    try:
        if cgidata.keys():
            # There are options to change
            change_options(mlist, category, cgidata, doc)
            # Let the list sanity check the changed values
            mlist.CheckValues()
        # Additional sanity checks
        if not mlist.digestable and not mlist.nondigestable:
            add_error_message(
                doc,
                _('''You have turned off delivery of both digest and
                non-digest messages.  This is an incompatible state of
                affairs.  You must turn on either digest delivery or
                non-digest delivery or your mailing list will basically be
                unusable.'''))

        if not mlist.digestable and len(mlist.GetDigestMembers()):
            add_error_message(
                doc,
                _('''You have digest members, but digests are turned
                off. Those people will not receive mail.'''))
        if not mlist.nondigestable and len(mlist.GetMembers()):
            add_error_message(
                doc,
                _('''You have regular list members but non-digestified mail is
                turned off.  They will receive mail until you fix this
                problem.'''))
        # Glom up the results page and print it out
        show_results(mlist, doc, category, category_suffix, cgidata)
        print doc.Format(bgcolor='#ffffff')
    finally:
        mlist.Save()
        mlist.Unlock()



def admin_overview(msg=''):
    # Show the administrative overview page, with the list of all the lists on
    # this host.  msg is an optional error message to display at the top of
    # the page.
    #
    # This page should be displayed in the server's default language, which
    # should have already been set.
    hostname = mm_cfg.DEFAULT_HOST_NAME
    legend = _('%(hostname)s mailing lists - Admin Links')
    # The html `document'
    doc = Document()
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)
    doc.SetTitle(legend)
    # The table that will hold everything
    table = Table(border=0, width="100%")
    table.AddRow([Center(Header(2, legend))])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0,
                      colspan=2, bgcolor="#99ccff")
    # Skip any mailing list that isn't advertised.
    advertised = []
    listnames = Utils.list_names()
    listnames.sort()
    for name in listnames:
        mlist = MailList.MailList(name, lock=0)
        if mlist.advertised:
            advertised.append(mlist)
    # Greeting depends on whether there was an error or not
    if msg:
        greeting = FontAttr(msg, color="ff5060", size="+1")
    else:
        greeting = _("Welcome!")

    welcome = []
    if not advertised:
        welcome.extend([
            greeting,
            _('<p>There currently are no publicly-advertised '),
            Link(mm_cfg.MAILMAN_URL, _('Mailman')),
            _(' mailing lists on %(hostname)s.'),
            ])
    else:
        welcome.extend([
            greeting,
            _('<p>Below is the collection of publicly-advertised '),
            Link(mm_cfg.MAILMAN_URL, _('Mailman')),
            _(' mailing lists on %(hostname)s.'),
            _(''' Click on a list name to visit the configuration pages for
            that list.'''),
            ])

    mailman_owner = mm_cfg.MAILMAN_OWNER
    extra = msg and _('right ') or ''
    welcome.extend([
        _('''To visit the administrators configuration page for an
        unadvertised list, open a URL similar to this one, but with a '/' and
        the %(extra)slist name appended.

        <p>General list information can be found at '''),
        Link(Utils.ScriptURL('listinfo'),
             _('the mailing list overview page')),
        '.',
        _('<p>(Send questions and comments to '),
        Link('mailto:%s' % mailman_owner, mailman_owner),
        '.)<p>',
        ])

    table.AddRow([Container(*welcome)])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0, colspan=2)

    if advertised:
        table.AddRow(['&nbsp;', '&nbsp;'])
        table.AddRow([Bold(_('List')), Bold(_('Description'))])
        for mlist in advertised:
            table.AddRow(
                [Link(mlist.GetScriptURL('admin'), Bold(mlist.real_name)),
                 mlist.description or Italic(_('[no description available]')),
                 ])

    doc.AddItem(table)
    doc.AddItem('<hr>')
    doc.AddItem(MailmanLogo())
    print doc.Format(bgcolor="#ffffff")



def option_help(mlist, varhelp):
    # The html page document
    doc = Document()
    doc.set_language(mlist.preferred_language)
    # Find out which category and variable help is being requested for.
    item = None
    reflist = varhelp.split('/')
    if len(reflist) == 2:
        category, varname = reflist
        options = get_config_options(mlist, category)
        for i in options:
            if i and i[0] == varname:
                item = i
                break
    # Print an error message if we couldn't find a valid one
    if not item:
        path_info = os.environ.get('PATH_INFO')
        bad = _('No valid variable details request not found: %(path_info)s')
        add_error_message(doc, bad)
        print doc.Format(bgcolor='#fffff')
        return
    # Get the details about the variable
    varname, kind, params, dependancies, description, elaboration = \
             get_item_characteristics(item)
    if elaboration is None:
        elaboration = description
    #
    # Set up the document
    realname = mlist.real_name
    legend = _("""%(realname)s Mailing list Configuration Help
    <br><em>%(varname)s</em> Option""")
    
    header = Table(width='100%')
    header.AddRow([Center(Header(3, legend))])
    header.AddCellInfo(max(header.GetCurrentRowIndex(), 0), 0,
                       colspan=2, bgcolor="#99ccff")
    doc.SetTitle(_("Mailman %(varname)s List Option Help"))
    doc.AddItem(header)
    doc.AddItem("<b>%s</b> (%s): %s<p>" % (varname, category, description))
    doc.AddItem("%s<p>" % elaboration)

    form = Form("%s/%s" % (mlist.GetScriptURL('admin'), category))
    valtab = Table(cellspacing=3, cellpadding=4)
    add_options_table_item(mlist, category, valtab, item, detailsp=0)
    form.AddItem(valtab)
    form.AddItem('<p>')
    form.AddItem(Center(submit_button()))
    doc.AddItem(Center(form))

    doc.AddItem(_("""<em><strong>Warning:</strong> changing this option here
    could cause other screens to be out-of-sync.  Be sure to reload any other
    pages that are displaying this option for this mailing list.  You can also
    """))

    doc.AddItem(Link('%s/%s' % (mlist.GetScriptURL('admin'), category),
                     _('return to the %(category)s options page.')))
    doc.AddItem('</em>')
    doc.AddItem(mlist.GetMailmanFooter())
    print doc.Format(bgcolor="#ffffff")



def show_results(mlist, doc, category, category_suffix, cgidata):
    # Produce the results page
    global CATEGORIES

    adminurl = mlist.GetScriptURL('admin')

    for k, v in CATEGORIES:
        if k == category:
            label = _(v)
            break

    # Set up the document's headers
    realname = mlist.real_name
    doc.SetTitle(_('%(realname)s Administration (%(label)s)'))
    doc.AddItem(Center(Header(2, _(
        '%(realname)s mailing list administration<br>%(label)s Section'))))
    doc.AddItem('<hr>')
    # This holds the two columns of links
    linktable = Table(valign='top')
    linktable.AddRow([Center(Bold(_("Configuration Categories"))),
                      Center(Bold(_("Other Administrative Activities")))])

    # The `other links' are stuff in the right column.
    otherlinks = UnorderedList()
    otherlinks.AddItem(Link(mlist.GetScriptURL('admindb'), 
                            _('Tend to pending administrative requests')))
    otherlinks.AddItem(Link(mlist.GetScriptURL('listinfo'),
                            _('Go to the general list information page')))
    otherlinks.AddItem(Link(mlist.GetScriptURL('edithtml'),
                            _('Edit the HTML for the public list pages')))
    otherlinks.AddItem(Link(mlist.GetBaseArchiveURL(),
                            _('Go to list archives')))
    otherlinks.AddItem(Link('%s/logout' % adminurl,
                            # BAW: What I really want is a blank line, but
                            # adding an &nbsp; won't do it because of the
                            # bullet added to the list item.
                            '<FONT SIZE="+2"><b>%s</b></FONT>' %
                            _('Logout')))
    # These are links to other categories and live in the left column
    categorylinks = UnorderedList()
    for k, v in CATEGORIES:
        url = '%s/%s' % (adminurl, k)
        # Translate
        v = _(v)
        if k == category:
            # Membership management has some subcategories
            if k == category == 'members':
                subcat_items = []
                subcat = Utils.GetPathPieces()[-1]
                if subcat == 'members':
                    subcat = 'list'
                for sub, text in (('list',   _('Membership List')),
                                  ('add',    _('Mass Subscription')),
                                  ('remove', _('Mass Removal'))):
                    if sub == subcat:
                        text = Bold('[%s]' % text).Format()
                    subcat_items.append(Link('%s/%s/%s' % (adminurl, k, sub),
                                             text))
                v += UnorderedList(*subcat_items).Format()
            else:
                v = Bold('[%s]' % v).Format()
        categorylinks.AddItem(Link('%s/%s' % (adminurl, k), v))
    # Add all the links to the links table...
    linktable.AddRow([categorylinks, otherlinks])
    linktable.AddRowInfo(max(linktable.GetCurrentRowIndex(), 0),
                         valign='top')
    # ...and add the links table to the document.
    doc.AddItem(linktable)
    doc.AddItem('<hr>')
    # Now we need to craft the form that will be submitted, which will contain
    # all the variable settings, etc.  This is a bit of a kludge because we
    # know that the autoreply and members categories supports file uploads.
    if category_suffix:
        encoding = None
        if category_suffix in ('autoreply', 'members'):
            # These have file uploads
            encoding = 'multipart/form-data'
        form = Form('%s/%s' % (adminurl, category_suffix), encoding=encoding)
    else:
        form = Form(adminurl)
    # And add the form
    doc.AddItem(form)
    # The general category supports changing the password.
    if category == 'general':
        andpassmsg = _('  (You can change your password there, too.)')
    else:
        andpassmsg = ''
    form.AddItem(
        _('''Make your changes below, and then submit them
        using the button at the bottom.''') +
        andpassmsg +
        '<p>')

    form.AddItem(show_variables(mlist, category, cgidata, doc, form))

    if category == 'general':
        form.AddItem(Center(password_inputs()))

    form.AddItem("<p>")
    form.AddItem(Center(submit_button()))
    form.AddItem(mlist.GetMailmanFooter())
    # main() formats and prints the document



def show_variables(mlist, category, cgidata, doc, form):
    # Produce the category specific variable options table
    if category == 'members':
        # Special case for members section.
        return membership_options(mlist, cgidata, doc, form)

    options = get_config_options(mlist, category)

    # The table containing the results
    table = Table(cellspacing=3, cellpadding=4)
    # Get and portray the text label for the category.
    for k, v in CATEGORIES:
        if k == category:
            label = _(v)
            break

    table.AddRow([Center(Header(2, label))])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0,
                          colspan=2, bgcolor="#99ccff")

    # Convenience
    def column_header(table=table):
        table.AddRow([Center(Bold(_('Description'))),
                      Center(Bold(_('Value')))])
        table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0,
                          width='15%')
        table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 1,
                          width='85%')

    did_col_header = 0
    for item in options:
        if type(item) == types.StringType:
            # The very first banner option (string in an options list) is
            # treated as a general description, while any others are
            # treated as section headers - centered and italicized...
            if did_col_header:
                item = "<center><i>" + item + "</i></center>"
            table.AddRow([item])
            table.AddCellInfo(max(table.GetCurrentRowIndex(), 0),
                                  0, colspan=2)
            if not did_col_header:
                # Do col header after very first string descr, if any...
                column_header()
                did_col_header = 1
        else:
            if not did_col_header:
                # ... but do col header before anything else.
                column_header()
                did_col_header = 1
            add_options_table_item(mlist, category, table, item)
    table.AddRow(['<br>'])
    table.AddCellInfo(table.GetCurrentRowIndex(), 0, colspan=2)
    return table



def add_options_table_item(mlist, category, table, item, detailsp=1):
    # Add a row to an options table with the item description and value.
    varname, kind, params, dependancies, descr, elaboration = \
             get_item_characteristics(item)
    if elaboration is None:
        elaboration = descr
    descr = get_item_gui_description(mlist, category, varname, descr, detailsp)
    val = get_item_gui_value(mlist, kind, varname, params)
    table.AddRow([descr, val])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 1,
                      bgcolor="#cccccc")
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0,
                      bgcolor="#cccccc")



def get_item_characteristics(record):
    # Break out the components of an item description from its description
    # record:
    #
    # 0 -- option-var name
    # 1 -- type
    # 2 -- entry size
    # 3 -- ?dependancies?
    # 4 -- Brief description
    # 5 -- Optional description elaboration
    if len(record) == 5:
        elaboration = None
        varname, kind, params, dependancies, descr = record
    elif len(record) == 6:
        varname, kind, params, dependancies, descr, elaboration = record
    else:
        raise ValueError, _('Badly formed options entry:\n %(record)s')
    return varname, kind, params, dependancies, descr, elaboration



def get_item_gui_value(mlist, kind, varname, params):
    """Return a representation of an item's settings."""
    if kind == mm_cfg.Radio or kind == mm_cfg.Toggle:
        #
        # if we are sending returning the option for subscribe
        # policy and this site doesn't allow open subscribes,
        # then we have to alter the value of mlist.subscribe_policy
        # as passed to RadioButtonArray in order to compensate
        # for the fact that there is one fewer option. correspondingly,
        # we alter the value back in the change options function -scott
        #
        # TBD: this is an ugly ugly hack.
        if varname[0] == '_':
            checked = 0
        else:
            checked = getattr(mlist, varname)
        if varname == 'subscribe_policy' and not mm_cfg.ALLOW_OPEN_SUBSCRIBE:
            checked = checked - 1
        return RadioButtonArray(varname, params, checked)
    elif (kind == mm_cfg.String or kind == mm_cfg.Email or
          kind == mm_cfg.Host or kind == mm_cfg.Number):
        return TextBox(varname, getattr(mlist, varname), params)
    elif kind == mm_cfg.Text:
        if params:
            r, c = params
        else:
            r, c = None, None
        val = getattr(mlist, varname)
        if not val:
            val = ''
        return TextArea(varname, val, r, c)
    elif kind == mm_cfg.EmailList:
        if params:
            r, c = params
        else:
            r, c = None, None
        res = NL.join(getattr(mlist, varname))
        return TextArea(varname, res, r, c, wrap='off')
    elif kind == mm_cfg.FileUpload:
        # like a text area, but also with uploading
        if params:
            r, c = params
        else:
            r, c = None, None
        val = getattr(mlist, varname)
        if not val:
            val = ''
        container = Container()
        container.AddItem(_('<em>Enter the text below, or...</em><br>'))
        container.AddItem(TextArea(varname, val, r, c))
        container.AddItem(_('<br><em>...specify a file to upload</em><br>'))
        container.AddItem(FileUpload(varname+'_upload', r, c))
        return container
    # jcrey - new to deal with language popup
    elif kind == mm_cfg.Select:
        if params:
           values, legend, selected = params
        else:
           values = mlist.GetAvailableLanguages()
           legend = map(_, map(Utils.GetLanguageDescr, values))
           selected = values.index(mlist.preferred_language)
        return SelectOptions(varname, values, legend, selected)



def get_item_gui_description(mlist, category, varname, descr, detailsp):
    # Return the item's description, with link to details.
    #
    # Details are not included if this is a VARHELP page, because that /is/
    # the details page!
    if detailsp:
        text = Container('<div ALIGN="right">' + descr + ' ',
                     Link(mlist.GetScriptURL('admin')
                              + '/?VARHELP=' + category + '/' + varname,
                          _('(Details)')),
                     '</div>').Format()
    else:
        text = '<div ALIGN="right">' + descr + '</div>'
    if varname[0] == '_':
        text = text + _('''<div ALIGN="right"><br><em><strong>Note:</strong>
        setting this value performs an immediate action but does not modify
        permanent state.</em></div>''')
    return text



def membership_options(mlist, cgidata, doc, form):
    # Figure out which subcategory we should display
    subcat = Utils.GetPathPieces()[-1]
    if subcat not in ('list', 'add', 'remove'):
        subcat = 'list'
    # Show the main stuff
    container = Container()
    header = Table(width="100%")
    # If we're in the list subcategory, show the membership list
    if subcat == 'add':
        header.AddRow([Center(Header(2, _('Mass Subscriptions')))])
        header.AddCellInfo(max(header.GetCurrentRowIndex(), 0), 0,
                           colspan=2, bgcolor='#99ccff')
        container.AddItem(header)
        mass_subscribe(mlist, container)
        return container
    if subcat == 'remove':
        header.AddRow([Center(Header(2, _('Mass Removals')))])
        header.AddCellInfo(max(header.GetCurrentRowIndex(), 0), 0,
                           colspan=2, bgcolor='#99ccff')
        container.AddItem(header)
        mass_remove(mlist, container)
        return container
    # Otherwise...
    header.AddRow([Center(Header(2, _('Membership List')))])
    header.AddCellInfo(max(header.GetCurrentRowIndex(), 0), 0,
                       colspan=2, bgcolor='#99ccff')
    container.AddItem(header)
    usertable = Table(width="90%", border='2')
    # If there are more members than allowed by chunksize, then we split the
    # membership up alphabetically.  Otherwise just display them all.
    chunksz = mlist.admin_member_chunksize
    all = mlist.GetMembers() + mlist.GetDigestMembers()
    all.sort(lambda x, y: cmp(x.lower(), y.lower()))
    # See if the query has a regular expression
    regexp = ''
    if cgidata.has_key('findmember'):
        regexp = cgidata['findmember'].value
        try:
            cre = re.compile(regexp, re.IGNORECASE)
        except re.error:
            add_error_message(doc, 'Bad regular expression: ' + regexp)
        else:
            all = [s for s in all if cre.search(s)]
    chunkindex = None
    bucket = None
    actionurl = None
    if len(all) < chunksz:
        members = all
    else:
        # Split them up alphabetically, and then split the alphabetical
        # listing by chunks
        buckets = {}
        for addr in all:
            members = buckets.setdefault(addr[0].lower(), [])
            members.append(addr)
        # Now figure out which bucket we want
        bucket = 'a'
        # POST methods, even if their actions have a query string, don't get
        # put into FieldStorage's keys :-(
        qs = cgi.parse_qs(os.environ['QUERY_STRING'])
        if qs.has_key('letter'):
            bucket = qs['letter'][0].lower()
            if bucket not in digits + lowercase:
                bucket = None
        if not bucket or not buckets.has_key(bucket):
            keys = buckets.keys()
            keys.sort()
            bucket = keys[0]
        members = buckets[bucket]
        action = mlist.GetScriptURL('admin') + '/members?letter=%s' % bucket
        if len(members) <= chunksz:
            form.set_action(action)
        else:
            i, r = divmod(len(members), chunksz)
            numchunks = i + (not not r * 1)
            # Now chunk them up
            chunkindex = 0
            if qs.has_key('chunk'):
                try:
                    chunkindex = int(qs['chunk'][0])
                except ValueError:
                    chunkindex = 0
                if chunkindex < 0 or chunkindex > numchunks:
                    chunkindex = 0
            members = members[chunkindex*chunksz:(chunkindex+1)*chunksz]
            # And set the action URL
            form.set_action(action + '&chunk=%s' % chunkindex)
    # So now members holds all the addresses we're going to display
    allcnt = len(all)
    if bucket:
        membercnt = len(members)
        usertable.AddRow([Center(Italic(_(
            '%(allcnt)s members total, %(membercnt)s shown')))])
    else:
        usertable.AddRow([Center(Italic(_('%(allcnt)s members total')))])
    usertable.AddCellInfo(usertable.GetCurrentRowIndex(),
                           usertable.GetCurrentCellIndex(),
                           bgcolor="#cccccc", colspan=9)
    # Add the alphabetical links
    if bucket:
        cells = []
        for letter in digits + lowercase:
            if not buckets.get(letter):
                continue
            url = mlist.GetScriptURL('admin') + '/members?letter=%s' % letter
            if letter == bucket:
                show = Bold('[%s]' % letter.upper()).Format()
            else:
                show = letter.upper()
            cells.append(Link(url, show).Format())
        joiner = '&nbsp;'*2 + '\n'
        usertable.AddRow([Center(joiner.join(cells))])
    usertable.AddCellInfo(usertable.GetCurrentRowIndex(),
                           usertable.GetCurrentCellIndex(),
                           bgcolor="#cccccc", colspan=9)
    usertable.AddRow([Center(h) for h in (_('member address<br>member name'),
                                          _('subscr'), _('hide'), _('nomail'),
                                          _('ack'), _('not metoo'),
                                          _('digest'), _('plain'),
                                          _('language'))])
    rowindex = usertable.GetCurrentRowIndex()
    for i in range(9):
        usertable.AddCellInfo(rowindex, i, bgcolor='#cccccc')
    # Find the longest name in the list
    if members:
        longest = max([len(s) for s in members])
    else:
        longest = 0
    # Now populate the rows
    for addr in members:
        link = Link(mlist.GetOptionsURL(addr, obscure=1),
                    mlist.GetUserSubscribedAddress(addr))
#        name = TextBox(addr + '_realname', 'NOT YET IMPLEMENTED', size=longest)
        cells = [link.Format() + '<br>' +
                 #name.Format() + '\n' +
                 Hidden('user', urllib.quote(addr)).Format(),
                 Center(CheckBox(addr + '_subscribed', 'on', 1).Format()),
                 ]
        for opt in ('hide', 'nomail', 'ack', 'notmetoo'):
            if mlist.GetUserOption(addr, MailCommandHandler.option_info[opt]):
                value = 'on'
                check = 1
            else:
                value = 'off'
                checked = 0
            box = CheckBox('%s_%s' % (addr, opt), value, checked)
            cells.append(Center(box).Format())
        if mlist.members.has_key(addr):
            cells.append(Center(CheckBox(addr + '_digest', 'off', 0).Format()))
        else:
            cells.append(Center(CheckBox(addr + '_digest', 'on', 1).Format()))
        if mlist.GetUserOption(addr, MailCommandHandler.option_info['plain']):
            value = 'on'
            checked = 1
        else:
            value = 'off'
            checked = 0
        cells.append(Center(CheckBox('%s_plain' % addr, value, checked)))
        # User's preferred language
        langpref = mlist.GetPreferredLanguage(addr)
        langs = mlist.GetAvailableLanguages()
        langdescs = [_(Utils.GetLanguageDescr(lang)) for lang in langs]
        try:
            selected = langs.index(langpref)
        except ValueError:
            selected = 0
        cells.append(Center(SelectOptions(addr + '_language', langs,
                                          langdescs, selected)).Format())
        usertable.AddRow(cells)
    # Add the usertable and a legend
    container.AddItem(Center(usertable))
    legend = UnorderedList()
    legend.AddItem(_('<b>subscr</b> -- Is the member subscribed?'))
    legend.AddItem(
        _("""<b>hide</b> -- Is the member's address concealed on
        the list of subscribers?"""))
    legend.AddItem(_('<b>nomail</b> -- Is delivery to the member disabled?'))
    legend.AddItem(
        _('''<b>ack</b> -- Does the member get acknowledgements of their
        posts?'''))
    legend.AddItem(
        _('''<b>not metoo</b> -- Does the member avoid copies of their own
        posts?'''))
    legend.AddItem(
        _('''<b>digest</b> -- Does the member get messages in digests?
        (otherwise, individual messages)'''))
    legend.AddItem(
        _('''<b>plain</b> -- If getting digests, does the member get plain
        text digests?  (otherwise, MIME)'''))
    legend.AddItem(_("<b>language</b> -- Language preferred by the user"))
    container.AddItem(legend.Format())

    # There may be additional chunks
    if chunkindex is not None:
        buttons = []
        url = mlist.GetScriptURL('admin') + '/members?letter=%s&' % bucket
        footer = _('''<p><em>To view more members, click on the appropriate
        range listed below:</em>''')
        chunkmembers = buckets[bucket]
        last = len(chunkmembers)
        for i in range(numchunks):
            if i == chunkindex:
                continue
            start = chunkmembers[i*chunksz]
            end = chunkmembers[min((i+1)*chunksz, last)-1]
            link = Link(url + 'chunk=%d' % i, _('from %(start)s to %(end)s'))
            buttons.append(link)
        buttons = UnorderedList(*buttons)
        container.AddItem(footer + buttons.Format() + '<p>')
    # Search for member
    container.AddItem(
        _('Find members by regular expression:') +
        TextBox('findmember', value=regexp, size='50%').Format() +
        SubmitButton('findmember_btn', 'Search...').Format())
    return container


def mass_subscribe(mlist, container):
    # MASS SUBSCRIBE
    t = Table(width='90%')
    # Ask whether to send a welcome message and/or to notify the admin
    t.AddRow([_('Send welcome message to this batch? ')
              + RadioButton('send_welcome_msg_to_this_batch', 0,
                            not mlist.send_welcome_msg).Format()
              + _(' no ')
              + RadioButton('send_welcome_msg_to_this_batch', 1,
                            mlist.send_welcome_msg).Format()
              + _(' yes ')])
    t.AddRow([_('Send notifications to the list owner? ')
              + RadioButton('send_notifications_to_list_owner', 0,
                            not mlist.admin_notify_mchanges).Format()
              + _(' no ')
              + RadioButton('send_notifications_to_list_owner', 1,
                            mlist.admin_notify_mchanges).Format()
              + _(' yes ')])
    t.AddRow([Italic(_('Enter one address per line below...')).Format()
              + '<br>'])
    t.AddRow([Center(TextArea(name='subscribees',
                              rows=10, cols='100%', wrap=None))])
    t.AddRow([Italic(_('...or specify a file to upload:'))])
    t.AddRow([FileUpload('subscribees_upload', cols='50').Format()])
    container.AddItem(Center(t))


def mass_remove(mlist, container):
    # MASS UNSUBSCRIBE
    t = Table(width='90%')
    t.AddRow([_('Send unsubscription acknowledgement to the user? ')
              + RadioButton('send_unsub_ack_to_this_batch', 0, 1).Format()
              + _(' no ')
              + RadioButton('send_unsub_ack_to_this_batch', 1, 0).Format()
              +_(' yes ')])
    t.AddRow([_('Send notifications to the list owner? ')
              + RadioButton('send_unsub_notifications_to_list_owner', 0,
                            not mlist.admin_notify_mchanges).Format()
              + _(' no ')
              + RadioButton('send_unsub_notifications_to_list_owner', 1,
                            mlist.admin_notify_mchanges).Format()
              + _(' yes ')])
    t.AddRow([Italic(_('Enter one address per line below...')).Format()
              + '<br>'])
    t.AddRow([Center(TextArea(name='unsubscribees',
                              rows=10, cols='100%', wrap=None))])
    t.AddRow([Italic(_('...or specify a file to upload:'))])
    t.AddRow([FileUpload('unsubscribees_upload', cols='50').Format()])
    container.AddItem(Center(t))



def password_inputs():
    change_pw_table = Table(bgcolor="#99cccc", border=0,
                            cellspacing=0, cellpadding=2,
                            valign="top")
    change_pw_table.AddRow(
        [Bold(Center(_('To Change The Administrator Password')))])
    change_pw_table.AddCellInfo(0, 0, align="left", colspan=2)
    old = Table(bgcolor="#99cccc", border=1,
                cellspacing=0, cellpadding=2, valign="top")
    old.AddRow(['<div ALIGN="right">' +
                _(" Enter current password:") +
                '</div>',
                PasswordBox('adminpw')])
    new = Table(bgcolor="#99cccc", border=1,
                cellspacing=0, cellpadding=2, valign="top")
    new.AddRow(['<div ALIGN="right">' + _(" Enter new password:") + '</div>',
                PasswordBox('newpw')])
    new.AddRow(['<div ALIGN="right">' + _("Confirm new password:") + '</div>',
                PasswordBox('confirmpw')])
    change_pw_table.AddRow([old, new])
    change_pw_table.AddCellInfo(1, 0, align="left", valign="top")
    #change_pw_table.AddCellInfo(1, 1, align="left", valign="top")
    return change_pw_table



def submit_button():
    submit = Table(bgcolor="#99ccff",
                   border=0, cellspacing=0, cellpadding=2)
    submit.AddRow([Bold(SubmitButton('submit', _('Submit Your Changes')))])
    submit.AddCellInfo(submit.GetCurrentRowIndex(), 0, align="middle")
    return submit



# Options processing
def get_valid_value(mlist, prop, my_type, val, dependant):
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
            # TBD: should have a way of displaying the results of the
            # operation.
            pass
        # Revert to the old value.
        return getattr(mlist, prop)
    elif my_type == mm_cfg.EmailList:
        def validp(addr):
            try:
                Utils.ValidateEmail(addr)
                return 1
            except Errors.EmailAddressError:
                return 0
        val = [addr for addr in [s.strip() for s in val.split(NL)]
               if validp(addr)]
        return val
    elif my_type == mm_cfg.Host:
        return val
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
            return getattr(mlist, prop)
        return num
    elif my_type == mm_cfg.Select:
        return val
    else:
        # Should never get here...
        return val



def change_options(mlist, category, cgidata, doc):
    confirmed = 0
    if cgidata.has_key('newpw'):
        if cgidata.has_key('confirmpw'):
            if cgidata.has_key('adminpw') and cgidata['adminpw'].value:
                try:
                    mlist.ConfirmAdminPassword(cgidata['adminpw'].value)
                    confirmed = 1
                except Errors.MMBadPasswordError:
                    add_error_message(doc,
                                      _('Incorrect administrator password'),
                                      tag='Error: ')
            if confirmed:
                new = cgidata['newpw'].value.strip()
                confirm = cgidata['confirmpw'].value.strip()
                if new == '' and confirm == '':
                    add_error_message(
                        doc,
                        _('Empty admin passwords are not allowed'),
                        tag='Error: ')
                elif new == confirm:
                    mlist.password = sha.new(new).hexdigest()
                    # Re-authenticate (to set new cookie)
                    mlist.WebAuthenticate(password=new, cookie='admin')
                else:
                    add_error_message(doc, _('Passwords did not match'),
                                      tag='Error: ')
        else:
            add_error_message(doc,
                              _('You must type in your new password twice'),
                              tag='Error: ')
    #
    # for some reason, the login page mangles important values for the list
    # such as .real_name so we only process these changes if the category
    # is not "members" and the request is not from the login page
    # -scott 19980515
    #
    if category != 'members' and \
            not cgidata.has_key("request_login") and \
            len(cgidata.keys()) > 1:
        # then
        if cgidata.has_key("subscribe_policy"):
            if not mm_cfg.ALLOW_OPEN_SUBSCRIBE:
                #
                # we have to add one to the value because the
                # page didn't present an open list as an option
                #
                page_setting = int(cgidata["subscribe_policy"].value)
                cgidata["subscribe_policy"].value = str(page_setting + 1)
        opt_list = get_config_options(mlist, category)
        for item in opt_list:
            if type(item) <> types.TupleType or len(item) < 5:
                continue
            property, kind, args, deps, desc = item[0:5]
            if cgidata.has_key(property+'_upload') and \
                   cgidata[property+'_upload'].value:
                val = cgidata[property+'_upload'].value
            elif not cgidata.has_key(property):
                continue
            else:
                val = cgidata[property].value
            value = get_valid_value(mlist, property, kind, val, deps)
            #
            # This is an ugly, ugly hack
            if property[0] == '_':
                # TBD: When turning on usenet->mail gating we want to
                # automatically catch up the newsgroup otherwise the mailing
                # list will suddently get flooded.  There should be a much
                # better way to do this (or for the admin to specify they want
                # this).
                if property == '_mass_catchup' and value:
                    mlist.usenet_watermark = None
            elif getattr(mlist, property) <> value:
                # TBD: Ensure that mlist.real_name differs only in letter
                # case.  Otherwise a security hole can potentially be opened
                # when using an external archiver.  This seems ad-hoc and
                # could use a more general security policy.
                if property == 'real_name' and \
                       value.lower() <> mlist._internal_name.lower():
                    # then don't install this value.
                    doc.AddItem(_("""<p><b>real_name</b> attribute not
                    changed!  It must differ from the list's name by case
                    only.<p>"""))
                    continue
                # Watch for changes to preferred_language.  If found, make
                # sure that the response is generated in the new language.
                if property == 'preferred_language':
                    i18n.set_language(value)
                setattr(mlist, property, value)
    # mass subscription, removal processing for members category
    subscriptions = ''
    if cgidata.has_key('subscribees'):
        subscriptions += cgidata['subscribees'].value
    if cgidata.has_key('subscribees_upload') and \
           cgidata['subscribees_upload'].value:
        subscriptions += cgidata['subscribees_upload'].value
    if subscriptions:
        subscriptions.replace('\r', '')
        names = filter(None,
                       [unquote(n.strip()) for n in subscriptions.split(NL)])
        send_welcome_msg = int(
            cgidata['send_welcome_msg_to_this_batch'].value)
        digest = 0
        if not mlist.digestable:
            digest = 0
        if not mlist.nondigestable:
            digest = 1
        subscribe_errors = []
        subscribe_success = []
        result = mlist.ApprovedAddMembers(names, None,
                                          digest, None, send_welcome_msg)
        for name in result.keys():
            if result[name] is None:
                subscribe_success.append(name)
            else:
                # `name' was not subscribed, find out why.  On failures,
                # result[name] is set from sys.exc_info()[:2]
                e, v = result[name]
                if e is Errors.MMAlreadyAMember:
                    subscribe_errors.append((name, _('Already a member')))
                elif e is Errors.MMBadEmailError:
                    if name == '':
                        name = '&lt;blank line&gt;'
                    subscribe_errors.append(
                        (name, _('Bad/Invalid email address')))
                elif e is Errors.MMHostileAddress:
                    subscribe_errors.append(
                        (name, _('Hostile Address (illegal characters)')))
        if subscribe_success:
            doc.AddItem(Header(5, _('Successfully Subscribed:')))
            doc.AddItem(UnorderedList(*subscribe_success))
            doc.AddItem('<p>')
            # ApprovedAddMembers will already have saved the list for us.
        if subscribe_errors:
            doc.AddItem(Header(5, _('Error Subscribing:')))
            items = ['%s -- %s' % (x0, x1) for x0, x1 in subscribe_errors]
            doc.AddItem(UnorderedList(*items))
            doc.AddItem('<p>')
    # Unsubscriptions
    removals = ''
    if cgidata.has_key('unsubscribees'):
        removals += cgidata['unsubscribees'].value
    if cgidata.has_key('unsubscribees_upload') and \
           cgidata['unsubscribees_upload'].value:
        removals += cgidata['unsubscribees_upload'].value
    if removals:
        removals.replace('\r', '')
        names = filter(None, [unquote(n.strip()) for n in removals.split(NL)])
        send_unsub_notifications = int(
            cgidata['send_unsub_notifications_to_list_owner'].value)
        userack = int(
            cgidata['send_unsub_ack_to_this_batch'].value)
        unsubscribe_errors = []
        unsubscribe_success = []
        for addr in names:
            try:
                mlist.DeleteMember(addr, whence='admin mass unsub',
                                   admin_notif=send_unsub_notifications,
                                   userack=userack)
                unsubscribe_success.append(addr)
            except Errors.MMNoSuchUserError:
                unsubscribe_errors.append(addr)
        if unsubscribe_success:
            doc.AddItem(Header(5, _('Successfully Unsubscribed:')))
            doc.AddItem(UnorderedList(*unsubscribe_success))
            doc.AddItem('<p>')
            # ApprovedAddMembers will already have saved the list for us.
        if unsubscribe_errors:
            doc.AddItem(Header(3, Bold(FontAttr(
                _('Cannot unsubscribe non-members:'),
                color='#ff0000', size='+2')).Format()))
            doc.AddItem(UnorderedList(*unsubscribe_errors))
            doc.AddItem('<p>')
    #
    # do the user options for members category
    if cgidata.has_key('user'):
        user = cgidata["user"]
        if type(user) is types.ListType:
            users = []
            for ui in range(len(user)):
                users.append(urllib.unquote(user[ui].value))
        else:
            users = [urllib.unquote(user.value)]
        errors = []
        for user in users:
            if not cgidata.has_key('%s_subscribed' % (user)):
                try:
                    mlist.DeleteMember(user)
                except Errors.MMNoSuchUserError:
                    errors.append((user, _('Not subscribed')))
                continue
            value = cgidata.has_key('%s_digest' % user)
            try:
                mlist.SetUserDigest(user, value, force=1)
            except (Errors.MMNotAMemberError,
                    Errors.MMAlreadyDigested,
                    Errors.MMAlreadyUndigested):
                pass

            if cgidata.has_key(user+'_language'):
                newlang = cgidata[user+'_language'].value
                oldlang = mlist.GetPreferredLanguage(user)
                if newlang <> oldlang:
                    mlist.SetPreferredLanguage(user, newlang)
                  
            for opt in ("hide", "nomail", "ack", "notmetoo", "plain"):
                opt_code = MailCommandHandler.option_info[opt]
                if cgidata.has_key("%s_%s" % (user, opt)):
                    mlist.SetUserOption(user, opt_code, 1, save_list=0)
                else:
                    mlist.SetUserOption(user, opt_code, 0, save_list=0)
        if errors:
            doc.AddItem(Header(5, _("Error Unsubscribing:")))
            items = ['%s -- %s' % (x[0], x[1]) for x in errors]
            doc.AddItem(apply(UnorderedList, tuple((items))))
            doc.AddItem("<p>")



def add_error_message(doc, errmsg, tag='Warning: ', *args):
    doc.AddItem(Header(3, Bold(FontAttr(
        _(tag), color="#ff0000", size="+2")).Format() +
                       Italic(errmsg % args).Format()))



def get_config_options(mlist, category):
    return mlist.GetConfigInfo()[category]
