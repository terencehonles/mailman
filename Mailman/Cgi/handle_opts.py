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

"""Process input to user options form."""

import sys
import os
import string
import cgi

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog
from Mailman.i18n import _



def PrintResults(mlist, operation, doc, results, user=None, lang=None):
    if lang is None:
        lang = mlist.preferred_language
    if user:
        url = '%s/%s' % (mlist.GetScriptURL('options'),
                         Utils.ObscureEmail(user))
        results = results + _('<p>Continue to ') + \
                  Link(url, _('edit your personal options')).Format() + \
                  '.'
    replacements = mlist.GetStandardReplacements(lang)
    replacements['<mm-results>'] = results
    replacements['<mm-operation>'] = operation
    output = mlist.ParseTags('handle_opts.html', replacements, lang)
    doc.AddItem(output)
    print doc.Format(bgcolor="#ffffff")
    # hrm...
    sys.exit(0)



def main():
    doc = Document()
    parts = Utils.GetPathPieces()
    if not parts or len(parts) < 2:
        doc.AddItem(Header(2, _("Error")))
        doc.AddItem(Bold(_("Invalid options to CGI script.")))
        print doc.Format(bgcolor="#ffffff")
        return

    listname = string.lower(parts[0])
    user = parts[1]

    try:
        mlist = MailList.MailList(listname)
    except Errors.MMListError, e:
        doc.AddItem(Header(2, _("Error")))
        doc.AddItem(Bold(_('No such list <em>%(listname)s</em>')))
        print doc.Format(bgcolor="#ffffff")
        syslog('error', 'No such list "%s": %s\n' % (listname, e))
        return

    try:
        process_form(mlist, user, doc)
    finally:
        mlist.Save()
        mlist.Unlock()



def process_form(mlist, user, doc):
    form = cgi.FieldStorage()
    error = 0
    operation = ""
    user = Utils.LCDomain(user)

    os.environ['LANG'] = pluser = mlist.GetPreferredLanguage(user)

    if not Utils.FindMatchingAddresses(user, mlist.members,
                                       mlist.digest_members):
        PrintResults(mlist, operation, doc,
                     _("%(user)s not a member!<p>"),
                     pluser)

    if form.has_key("unsub"):
        operation = _("Unsubscribe")
        if not form.has_key("upw"):
            PrintResults(
                mlist, operation, doc,
                _("You must give your password to unsubscribe.") + "<p>",
                user, pluser)
        else:
            try:
                pw = form["upw"].value
                if mlist.ConfirmUserPassword(user, pw):
                    mlist.DeleteMember(user, "web cmd")
            except Errors.MMListNotReadyError:
                PrintResults(mlist, operation, doc,
                             _("List is not functional."),
                             user, pluser)
            except Errors.MMNoSuchUserError:
                PrintResults(mlist, operation, doc,
                             _("You seem to already be not a member.") + "<p>",
                             user, pluser)
            except Errors.MMBadUserError:
                PrintResults(mlist, operation, doc,
                             _("Your account has gone awry - "
                             "please contact the list administrator!") + "<p>",
                             user, pluser)
            except Errors.MMBadPasswordError:
                PrintResults(mlist, operation, doc,
                             _("That password was incorrect.") + "<p>")
        PrintResults(mlist, operation, doc,
                     _("You have been unsubscribed.") + "<p>", None, pluser)

    elif form.has_key("emailpw"):
        try:
            mlist.MailUserPassword(user)
            PrintResults(mlist, operation, doc,
                         _("A reminder of your password "
                           "has been emailed to you.") + "<p>", user, pluser)
        except Errors.MMBadUserError:
            PrintResults(mlist, operation, doc,
                         _("The password entry for `%(user)s' has not "
                         'been found.  The list administrator is being '
                         'notified.<p>'), user, pluser)

    elif form.has_key("othersubs"):
        if not form.has_key('othersubspw'):
            PrintResults(mlist, operation, doc,
                         _("You must specify your password."), user, pluser)
        else:
            try:
                mlist.ConfirmUserPassword(user, form['othersubspw'].value)
            except Errors.MMListNotReadyError:
                PrintResults(mlist, operation, doc,
                             _("The list is currently not functional."),
                             user, pluser)
            except Errors.MMNotAMemberError:
                PrintResults(mlist, operation, doc,
                             _("You seem to no longer be a list member."),
                             user, pluser)
            except Errors.MMBadPasswordError:
                PrintResults(mlist, operation, doc, _("Incorrect password."),
                             user, pluser)
            except Errors.MMBadUserError:
                PrintResults(
                    mlist, operation, doc,
                    _("You have no password. Contact the list administrator."),
                    user, pluser)

            hostname = mlist.host_name
            doc.AddItem(
                Header(2,
                       _("List Subscriptions for %(user)s on %(hostname)s")
                       ))
            doc.AddItem(_("Click a link to visit your options page for"
                          " that mailing list:"))

            def optionslinks(listname, user=user):
                mlist = MailList.MailList(listname, lock=0)
                addrs = Utils.FindMatchingAddresses(user, mlist.members,
                                                    mlist.digest_members)
                if addrs:
                    addr = Utils.ObscureEmail(addrs[0])
                    if mlist.obscure_addresses:
                        addr = Utils.ObscureEmail(addr)
                    url = mlist.GetOptionsURL(addr)
                    link = Link(url, mlist.real_name)
                    return mlist.internal_name(), link

            all_links = filter(None, map(optionslinks, Utils.list_names()))
            all_links.sort()
            items = OrderedList()
            for name, link in all_links:
                items.AddItem(link)
            doc.AddItem(items)
            print doc.Format(bgcolor="#ffffff")

    elif form.has_key("changepw"):
        if form.has_key('opw') and \
                form.has_key('newpw') and \
                form.has_key('confpw'):
            # then
            try:
                mlist.ConfirmUserPassword(user, form['opw'].value)
                mlist.ChangeUserPassword(user, form['newpw'].value,
                                         form['confpw'].value)
            except Errors.MMListNotReadyError:
                PrintResults(mlist, operation, doc,
                             _("The list is currently not functional."),
                             user, pluser)
            except Errors.MMNotAMemberError:
                PrintResults(mlist, operation, doc,
                             _("You seem to no longer be a list member."),
                             user, pluser)
            except Errors.MMBadPasswordError:
                PrintResults(mlist, operation, doc,
                             _("The old password you supplied was incorrect."),
                             user, pluser)
            except Errors.MMPasswordsMustMatch:
                PrintResults(mlist, operation, doc, _("Passwords must match."),
                             user, pluser)

            PrintResults(mlist, operation, doc,
                         _("Your password has been changed."),
                         user, pluser)
        else:
            PrintResults(mlist, operation, doc,
                         _("You must specify your old password,"
                           " and your new password twice."), user, pluser)

    else:
        # if key doesn't exist, or its value can't be int()'ified, return the
        # current value (essentially a noop)
        def getval(key, default, form=form):
            if form.has_key(key):
                try:
                    return int(form[key].value)
                except ValueError:
                    return default
            return default

        useropt = mlist.GetUserOption
        digest_value = getval('digest', useropt(user, mm_cfg.Digests))
        mime = getval('mime', useropt(user, mm_cfg.DisableMime))
        dont_receive = getval('dontreceive',
                              useropt(user, mm_cfg.DontReceiveOwnPosts))
        ack_posts = getval('ackposts', useropt(user, mm_cfg.AcknowledgePosts))
        disable_mail = getval('disablemail',
                              useropt(user, mm_cfg.DisableDelivery))
        conceal = getval('conceal', useropt(user, mm_cfg.ConcealSubscription))

        if not form.has_key("digpw"):
            PrintResults(mlist, operation, doc,
                         _("You must supply a password to change options."),
                         user, pluser)
        try:
            mlist.ConfirmUserPassword(user, form['digpw'].value)
        except Errors.MMAlreadyDigested:
            pass
        except Errors.MMAlreadyUndigested:
            pass
        except Errors.MMMustDigestError:
            PrintResults(mlist, operation, doc,
                         _("List only accepts digest members."), user, pluser)
        except Errors.MMCantDigestError:
            PrintResults(mlist, operation, doc,
                         _("List doesn't accept digest members."),
                         user, pluser)
        except Errors.MMNotAMemberError:
            PrintResults(mlist, operation, doc,
                         _("%(user)s isn't subscribed to this list."),
                         user, pluser)
        except Errors.MMListNotReadyError:
            PrintResults(mlist, operation, doc, _("List is not functional."),
                         user, pluser)
        except Errors.MMNoSuchUserError:
            PrintResults(mlist, operation, doc,
                         _("%(user)s is not subscribed to this list."),
                         user, pluser)
        except Errors.MMBadPasswordError:
            PrintResults(mlist, operation, doc,
                         _("You gave the wrong password."), user, pluser)

        # jcrey: read user's preferred language
        try:
           pluser = form['language'].value
        except ValueError:
           pluser = mlist.GetPreferredLanguage(user) 

        mlist.SetPreferredLanguage(user, pluser)

        mlist.SetUserOption(user, mm_cfg.DisableDelivery, disable_mail)
        mlist.SetUserOption(user, mm_cfg.DontReceiveOwnPosts, dont_receive)
        mlist.SetUserOption(user, mm_cfg.AcknowledgePosts, ack_posts)
        mlist.SetUserOption(user, mm_cfg.DisableMime, mime)
        msg = _('You have successfully set your options.')
        try:
            mlist.SetUserDigest(user, digest_value)
            # digest mode changed from on to off, so send the current digest
            # to the user.
            if digest_value == 0:
                PrintResults(mlist, operation, doc,
                             _('You may get one last digest.'), user, pluser)
        except (Errors.MMAlreadyDigested, Errors.MMAlreadyUndigested):
            pass
        except Errors.MMCantDigestError:
            msg = _('''The list administrator has disabled digest delivery for
            this list, so your delivery option has not been set.  However your
            other options have been set successfully.''')
        except Errors.MMMustDigestError:
            msg = _('''The list administrator has disabled non-digest delivery
            for this list, so your delivery option has not been set.  However
            your other options have been set successfully.''')
        mlist.SetUserOption(user, mm_cfg.ConcealSubscription, conceal)
        PrintResults(mlist, operation, doc, msg, user, pluser)
