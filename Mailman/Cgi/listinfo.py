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

"""Produce listinfo page, primary web entry-point to mailing lists.
"""

# No lock needed in this script, because we don't change data.

import os
import cgi

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog

# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)



def main():
    parts = Utils.GetPathPieces()
    if not parts:
        listinfo_overview()
        return

    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        listinfo_overview(_('No such list <em>%(listname)s</em>'))
        syslog('error', 'No such list "%s": %s' % (listname, e))
        return

    # See if the user want to see this page in other language
    form = cgi.FieldStorage()
    if form.has_key('language'):
        language = form['language'].value
    else:
        # No?  Okay, use the list's language
        language = mlist.preferred_language

    i18n.set_language(language)

    list_listinfo(mlist, language)



def listinfo_overview(msg=''):
    # Present the general listinfo overview
    #
    # TBD: We need a portable way to determine the host by which we are being
    # visited!  An absolute URL would do...
    http_host = os.environ.get('HTTP_HOST', os.environ.get('SERVER_NAME'))
    port = os.environ.get('SERVER_PORT')
    # Strip off the port if there is one
    if port and http_host[-len(port)-1:] == ':'+port:
        http_host = http_host[:-len(port)-1]
    if mm_cfg.VIRTUAL_HOST_OVERVIEW and http_host:
	hostname = http_host
    else:
	hostname = mm_cfg.DEFAULT_HOST_NAME

    # Set up the document and assign it the correct language.  The only one we
    # know about at the moment is the server's default.
    doc = Document()
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

    legend = _("%(hostname)s Mailing Lists")
    doc.SetTitle(legend)

    table = Table(border=0, width="100%")
    table.AddRow([Center(Header(2, legend))])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0,
                      colspan=2, bgcolor="#99ccff")

    # Skip any mailing lists that isn't advertised.
    advertised = []
    listnames = Utils.list_names()
    listnames.sort()

    for name in listnames:
	mlist = MailList.MailList(name, lock=0)
	if mlist.advertised:
	    if mm_cfg.VIRTUAL_HOST_OVERVIEW and \
                    http_host and \
                    http_host.find(mlist.web_page_url) == -1 and \
                    mlist.web_page_url.find(http_host) == -1:
		# List is for different identity of this host - skip it.
		continue
	    else:
		advertised.append(mlist)

    if msg:
	greeting = FontAttr(msg, color="ff5060", size="+1")
    else:
	greeting = FontAttr(_('Welcome!'), size='+2')

    welcome = [greeting]
    if not advertised:
        welcome.extend(
            ('<p>' + 
             _(' There currently are no publicly-advertised '),
             Link(mm_cfg.MAILMAN_URL, 'Mailman'),
             _(' mailing lists on %(hostname)s.')))
    else:
        welcome.append(
            _('''<p>Below is a listing of all the public mailing lists on
            %(hostname)s.  Click on a list name to get more information about
            the list, or to subscribe, unsubscribe, and change the preferences
            on your subscription.'''))

    # set up some local variables
    adj = msg and _('right') or ''
    welcome.extend(
        (_(''' To visit the info page for an unadvertised list,
        a URL similar to this one, but with a '/' and the %(adj)s
        list name appended.
        <p>List administrators, you can visit '''),
         Link(Utils.ScriptURL('admin'),
              _('the list admin overview page')),
         _(''' to find the management interface for your list.
         <p>Send questions or comments to '''),
         Link('mailto:' + mm_cfg.MAILMAN_OWNER,
              mm_cfg.MAILMAN_OWNER),
         '.<p>'))

    table.AddRow([apply(Container, welcome)])
    table.AddCellInfo(max(table.GetCurrentRowIndex(), 0), 0, colspan=2)

    if advertised:
        table.AddRow(['&nbsp;', '&nbsp;'])
        table.AddRow([Bold(FontAttr(_('List'), size='+2')),
                      Bold(FontAttr(_('Description'), size='+2'))
                      ])
    for mlist in advertised:
        table.AddRow(
            [Link(mlist.GetScriptURL('listinfo'), Bold(mlist.real_name)),
             mlist.description or Italic(_('[no description available]'))])

    doc.AddItem(table)
    doc.AddItem('<hr>')
    doc.AddItem(MailmanLogo())
    print doc.Format(bgcolor="#ffffff")



def list_listinfo(mlist, lang):
    # Generate list specific listinfo
    doc = HeadlessDocument()
    doc.set_language(lang)

    replacements = mlist.GetStandardReplacements(lang)

    if not mlist.digestable or not mlist.nondigestable:
        replacements['<mm-digest-radio-button>'] = ""
        replacements['<mm-undigest-radio-button>'] = ""
    else:
        replacements['<mm-digest-radio-button>'] = mlist.FormatDigestButton()
        replacements['<mm-undigest-radio-button>'] = \
                                                   mlist.FormatUndigestButton()
    replacements['<mm-plain-digests-button>'] = \
                                              mlist.FormatPlainDigestsButton()
    replacements['<mm-mime-digests-button>'] = mlist.FormatMimeDigestsButton()
    replacements['<mm-subscribe-box>'] = mlist.FormatBox('email', size=30)
    replacements['<mm-subscribe-button>'] = mlist.FormatButton(
        'email-button', text=_('Subscribe'))
    replacements['<mm-new-password-box>'] = mlist.FormatSecureBox('pw')
    replacements['<mm-confirm-password>'] = mlist.FormatSecureBox('pw-conf')
    replacements['<mm-subscribe-form-start>'] = mlist.FormatFormStart(
        'subscribe')
    replacements['<mm-roster-form-start>'] = mlist.FormatFormStart('roster')
    replacements['<mm-editing-options>'] = mlist.FormatEditingOption(lang)
    replacements['<mm-info-button>'] = SubmitButton('UserOptions',
                                                    _('Edit Options')).Format()
    replacements['<mm-roster-option>'] = mlist.FormatRosterOptionForUser(lang)
    replacements['<mm-displang-box>'] = mlist.FormatButton('displang-button',
                             text = _("See this page in"))
    replacements['<mm-lang-form-start>'] = mlist.FormatFormStart('listinfo')

    # Do the expansion.
    doc.AddItem(mlist.ParseTags('listinfo.html', replacements, lang))
    print doc.Format()



if __name__ == "__main__":
    main()
