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

"""Produce and handle the member options."""

import os
import cgi
import signal

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog

SLASH = '/'
SETLANGUAGE = -1

# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)



def main():
    doc = Document()
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

    parts = Utils.GetPathPieces()
    if not parts or len(parts) < 2:
        title = _('CGI script error')
        doc.SetTitle(title)
        doc.AddItem(Header(2, title))
        add_error_message(doc, _('Invalid options to CGI script.'))
        doc.AddItem('<hr>')
        doc.AddItem(MailmanLogo())
        print doc.Format()
        return

    # get the list and user's name
    listname = parts[0].lower()
    # open list
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        title = _('CGI script error')
        doc.SetTitle(title)
        doc.AddItem(Header(2, title))
        add_error_message(doc, _('No such list <em>%(listname)s</em>'))
        doc.AddItem('<hr>')
        doc.AddItem(MailmanLogo())
        print doc.Format()
        syslog('error', 'No such list "%s": %s\n' % (listname, e))
        return

    # Now we know which list is requested, so we can set the language to the
    # list's preferred language.
    i18n.set_language(mlist.preferred_language)
    doc.set_language(mlist.preferred_language)

    # Sanity check the user
    user = Utils.UnobscureEmail(SLASH.join(parts[1:]))
    user = Utils.LCDomain(user)
    if not mlist.IsMember(user):
        realname = mlist.real_name
        title = _('CGI script error')
        doc.SetTitle(title)
        doc.AddItem(Header(2, title))
        add_error_message(
            doc,
            _('List "%(realname)s" has no such member: %(user)s.'))
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format()
        return

    # Find the case preserved email address (the one the user subscribed with)
    lcuser = mlist.FindUser(user)
    cpuser = mlist.GetUserSubscribedAddress(lcuser)
    if lcuser == cpuser:
        cpuser = None

    # And now we know the user making the request, so set things up for the
    # user's preferred language.
    userlang = mlist.GetPreferredLanguage(user)
    doc.set_language(userlang)
    i18n.set_language(userlang)

    # Are we processing an unsubscription request from the login screen?
    cgidata = cgi.FieldStorage()
    if cgidata.has_key('login-unsub'):
        # Because they can't supply a password for unsubscribing, we'll need
        # to do the confirmation dance.
        mlist.ConfirmUnsubscription(user, userlang)
        add_error_message(
            doc,
            _('The confirmation email has been sent.'),
            tag='')
        loginpage(mlist, doc, user, cgidata)
        print doc.Format()
        return

    # Are we processing a password reminder from the login screen?
    if cgidata.has_key('login-remind'):
        mlist.MailUserPassword(user)
        add_error_message(
            doc,
            _('A reminder of your password has been emailed to you.'),
            tag='')
        loginpage(mlist, doc, user, cgidata)
        print doc.Format()
        return

    # Authenticate, possibly using the password supplied in the login page
    password = cgidata.getvalue('password', '').strip()

    if not mlist.WebAuthenticate((mm_cfg.AuthUser,
                                  mm_cfg.AuthListAdmin,
                                  mm_cfg.AuthSiteAdmin),
                                 password, user):
        # Not authenticated, so throw up the login page again.  If they tried
        # to authenticate via cgi (instead of cookie), then print an error
        # message.
        if cgidata.has_key('login'):
            add_error_message(doc, _('Authentication failed.'))

        loginpage(mlist, doc, user, cgidata)
        print doc.Format()
        return

    # From here on out, the user is okay to view and modify their membership
    # options.  The first set of checks does not require the list to be
    # locked.

    if cgidata.has_key('logout'):
        print mlist.ZapCookie(mm_cfg.AuthUser, user)
        loginpage(mlist, doc, user, cgidata)
        print doc.Format()
        return

    if cgidata.has_key('emailpw'):
        mlist.MailUserPassword(user)
        options_page(
            mlist, doc, user, cpuser, userlang,
            _('A reminder of your password has been emailed to you.'))
        print doc.Format()
        return

    if cgidata.has_key('othersubs'):
        hostname = mlist.host_name
        title = _('List subscriptions for %(user)s on %(hostname)s')
        doc.SetTitle(title)
        doc.AddItem(Header(2, title))
        doc.AddItem(_('''Click on a link to visit your options page for the
        requested mailing list.'''))

        # Troll through all the mailing lists that match host_name and see if
        # the user is a member.  If so, add it to the list.
        onlists = []
        for gmlist in lists_of_member(mlist.host_name, user):
            url = gmlist.GetOptionsURL(user)
            link = Link(url, gmlist.real_name)
            onlists.append((gmlist.real_name, link))
        onlists.sort()
        items = OrderedList(*[link for name, link in onlists])
        doc.AddItem(items)
        print doc.Format()
        return

    if cgidata.has_key('change-of-address'):
        newaddr = cgidata.getvalue('new-address')
        confirmaddr = cgidata.getvalue('confirm-address')
        if not newaddr or not confirmaddr:
            options_page(mlist, doc, user, cpuser, userlang,
                         _('Addresses may not be blank'))
            print doc.Format()
            return
        if newaddr <> confirmaddr:
            options_page(mlist, doc, user, cpuser, userlang,
                         _('Addresses did not match!'))
            print doc.Format()
            return

        # See if the user wants to change their email address globally
        globally = cgidata.getvalue('changeaddr-globally')

        # Standard sigterm handler.
        def sigterm_handler(signum, frame, mlist=mlist):
            mlist.Unlock()
            sys.exit(0)

        # Register the pending change after the list is locked
        msg = _('A confirmation message has been sent to %(newaddr)s')
        mlist.Lock()
        try:
            try:
                signal.signal(signal.SIGTERM, sigterm_handler)
                mlist.ChangeMemberAddress(user, newaddr, globally)
                mlist.Save()
            finally:
                mlist.Unlock()
        except Errors.MMBadEmailError:
            msg = _('Bad email address provided')
        except Errors.MMHostileAddress:
            msg = _('Illegal email address provided')
        except Errors.MMAlreadyAMember:
            msg = _('%(newaddr)s is already a member of the list.')

        options_page(mlist, doc, user, cpuser, userlang, msg)
        print doc.Format()
        return

    if cgidata.has_key('changepw'):
        newpw = cgidata.getvalue('newpw')
        confirmpw = cgidata.getvalue('confpw')
        if not newpw or not confirmpw:
            options_page(mlist, doc, user, cpuser, userlang,
                         _('Passwords may not be blank'))
            print doc.Format()
            return
        if newpw <> confirmpw:
            options_page(mlist, doc, user, cpuser, userlang,
                         _('Passwords did not match!'))
            print doc.Format()
            return

        # See if the user wants to change their passwords globally
        if cgidata.getvalue('pw-globally'):
            mlists = lists_of_member(mlist.host_name, user)
        else:
            mlists = [mlist]

        for gmlist in mlists:
            change_password(gmlist, user, newpw, confirmpw)

        # Regenerate the cookie so a re-authorization isn't necessary
        print mlist.MakeCookie(mm_cfg.AuthUser, user)
        options_page(mlist, doc, user, cpuser, userlang,
                     _('Password successfully changed.'))
        print doc.Format()
        return

    if cgidata.has_key('unsub'):
        # Was the confirming check box turned on?
        if not cgidata.getvalue('unsubconfirm'):
            options_page(
                mlist, doc, user, cpuser, userlang,
                _('''You must confirm your unsubscription request by turning
                on the checkbox below the <em>Unsubscribe</em> button.  You
                have not been unsubscribed!'''))
            print doc.Format()
            return

        # Standard signal handler
        def sigterm_handler(signum, frame, mlist=mlist):
            mlist.Unlock()
            sys.exit(0)

        # Okay, zap them.  Leave them sitting at the list's listinfo page.  We
        # must own the list lock, and we want to make sure the user (BAW: and
        # list admin?) is informed of the removal.
        mlist.Lock()
        try:
            signal.signal(signal.SIGTERM, sigterm_handler)
            mlist.DeleteMember(user, _('via the member options page'),
                               admin_notif=1, userack=1)
            mlist.Save()
        finally:
            mlist.Unlock()
        # Now throw up some results page, with appropriate links.  We can't
        # drop them back into their options page, because that's gone now!
        fqdn_listname = mlist.GetListEmail()
        owneraddr = mlist.GetOwnerEmail()
        url = mlist.GetScriptURL('listinfo', absolute=1)

        title = _('Unsubscription results')
        doc.SetTitle(title)
        doc.AddItem(Header(2, title))
        doc.AddItem(_("""You have been successfully unsubscribed from the
        mailing list %(fqdn_listname)s.  If you were receiving digest
        deliveries you may get one more digest.  If you have any questions
        about your unsubscription, please contact the list owners at
        %(owneraddr)s."""))
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format()
        return

    if cgidata.has_key('options-submit'):
        # Digest action flags
        digestwarn = 0
        cantdigest = 0
        mustdigest = 0

        newvals = []
        # First figure out which options have changed.  The item names come
        # from FormatOptionButton() in HTMLFormatter.py
        for item, flag in (('digest',      mm_cfg.Digests),
                           ('mime',        mm_cfg.DisableMime),
                           ('dontreceive', mm_cfg.DontReceiveOwnPosts),
                           ('ackposts',    mm_cfg.AcknowledgePosts),
                           ('disablemail', mm_cfg.DisableDelivery),
                           ('conceal',     mm_cfg.ConcealSubscription),
                           ('remind',      mm_cfg.SuppressPasswordReminder),
                           ):
            try:
                newval = int(cgidata.getvalue(item))
            except (TypeError, ValueError):
                newval = None

            # Skip this option if there was a problem or it wasn't changed
            if newval is None or newval == mlist.GetUserOption(user, flag):
                continue

            newvals.append((flag, newval))

            # The user language is handled a little differently
            userlang = cgidata.getvalue('language')
            if userlang not in mlist.GetAvailableLanguages():
                newvals.append((SETLANGUAGE, mlist.preferred_language))
            else:
                newvals.append((SETLANGUAGE, userlang))

        # The standard sigterm handler (see above)
        def sigterm_handler(signum, frame, mlist=mlist):
            mlist.Unlock()
            sys.exit(0)

        # Now, lock the list and perform the changes
        mlist.Lock()
        try:
            signal.signal(signal.SIGTERM, sigterm_handler)
            # `values' is a tuple of flags and the web values
            for flag, newval in newvals:
                # Handle language settings differently
                if flag == SETLANGUAGE:
                    mlist.SetPreferredLanguage(user, newval)
                    continue

                mlist.SetUserOption(user, flag, newval, save_list=0)

                # Digests also need another setting, which is a bit bogus, as
                # SetUserOption() should be taught about this special step.
                if flag == mm_cfg.Digests:
                    try:
                        mlist.SetUserDigest(user, newval)
                        if newval == 0:
                            digestwarn = 1
                    except (Errors.MMAlreadyDigested,
                            Errors.MMAlreadyUndigested):
                        pass
                    except Errors.MMCantDigestError:
                        cantdigest = 1
                    except Errors.MMMustDigestError:
                        mustdigest = 1
            # All done
            mlist.Save()
        finally:
            mlist.Unlock()
        
        # The enable/disable option and the password remind option may have
        # their global flags sets.
        global_enable = None
        if cgidata.getvalue('deliver-globally'):
            # Yes, this is inefficient, but the list is so small it shouldn't
            # make much of a difference.
            for flag, newval in newvals:
                if flag == mm_cfg.DisableDelivery:
                    global_enable = newval
                    break

        global_remind = None
        if cgidata.getvalue('remind-globally'):
            for flag, newval in newvals:
                if flag == mm_cfg.SuppressPasswordReminder:
                    global_remind = newval
                    break

        if global_enable is not None or global_remind is not None:
            for gmlist in lists_of_member(mlist.host_name, user):
                global_options(gmlist, user, global_enable, global_remind)

        # Now print the results
        if cantdigest:
            msg = _('''The list administrator has disabled digest delivery for
            this list, so your delivery option has not been set.  However your
            other options have been set successfully.''')
        elif mustdigest:
            msg = _('''The list administrator has disabled non-digest delivery
            for this list, so your delivery option has not been set.  However
            your other options have been set successfully.''')
        else:
            msg = _('You have successfully set your options.')

        if digestwarn:
            msg += _('You may get one last digest.')

        options_page(mlist, doc, user, cpuser, userlang, msg)
        print doc.Format()
        return

    options_page(mlist, doc, user, cpuser, userlang)
    print doc.Format()



def options_page(mlist, doc, user, cpuser, userlang, message=''):
    # The bulk of the document will come from the options.html template, which
    # includes it's own html armor (head tags, etc.).  Suppress the head that
    # Document() derived pages get automatically.
    doc.suppress_head = 1

    if mlist.obscure_addresses:
        presentable_user = Utils.ObscureEmail(user, for_text=1)
        if cpuser is not None:
            cpuser = Utils.ObscureEmail(cpuser, for_text=1)
    else:
        presentable_user = user

    # Do replacements
    replacements = mlist.GetStandardReplacements(userlang)
    replacements['<mm-results>'] = Bold(FontSize('+1', message)).Format()
    replacements['<mm-digest-radio-button>'] = mlist.FormatOptionButton(
        mm_cfg.Digests, 1, user)
    replacements['<mm-undigest-radio-button>'] = mlist.FormatOptionButton(
        mm_cfg.Digests, 0, user)
    replacements['<mm-plain-digests-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableMime, 1, user)
    replacements['<mm-mime-digests-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableMime, 0, user)
    replacements['<mm-delivery-enable-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableDelivery, 0, user)
    replacements['<mm-delivery-disable-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableDelivery, 1, user)
    replacements['<mm-disabled-notice>'] = mlist.FormatDisabledNotice(user)
    replacements['<mm-dont-ack-posts-button>'] = mlist.FormatOptionButton(
        mm_cfg.AcknowledgePosts, 0, user)
    replacements['<mm-ack-posts-button>'] = mlist.FormatOptionButton(
        mm_cfg.AcknowledgePosts, 1, user)
    replacements['<mm-receive-own-mail-button>'] = mlist.FormatOptionButton(
        mm_cfg.DontReceiveOwnPosts, 0, user)
    replacements['<mm-dont-receive-own-mail-button>'] = (
        mlist.FormatOptionButton(mm_cfg.DontReceiveOwnPosts, 1, user))
    replacements['<mm-dont-get-password-reminder-button>'] = (
        mlist.FormatOptionButton(mm_cfg.SuppressPasswordReminder, 1, user))
    replacements['<mm-get-password-reminder-button>'] = (
        mlist.FormatOptionButton(mm_cfg.SuppressPasswordReminder, 0, user))
    replacements['<mm-public-subscription-button>'] = (
        mlist.FormatOptionButton(mm_cfg.ConcealSubscription, 0, user))
    replacements['<mm-hide-subscription-button>'] = mlist.FormatOptionButton(
        mm_cfg.ConcealSubscription, 1, user)
    replacements['<mm-unsubscribe-button>'] = (
        mlist.FormatButton('unsub', _('Unsubscribe')) + '<br>' +
        CheckBox('unsubconfirm', 1, checked=0).Format() +
        _('<em>Yes, I really want to unsubscribe</em>'))
    replacements['<mm-new-pass-box>'] = mlist.FormatSecureBox('newpw')
    replacements['<mm-confirm-pass-box>'] = mlist.FormatSecureBox('confpw')
    replacements['<mm-change-pass-button>'] = (
        mlist.FormatButton('changepw', _("Change My Password")))
    replacements['<mm-other-subscriptions-submit>'] = (
        mlist.FormatButton('othersubs',
                           _('List my other subscriptions')))
    replacements['<mm-form-start>'] = (
        mlist.FormatFormStart('options', user))
    replacements['<mm-user>'] = user
    replacements['<mm-presentable-user>'] = presentable_user
    replacements['<mm-email-my-pw>'] = mlist.FormatButton(
        'emailpw', (_('Email My Password To Me')))
    replacements['<mm-umbrella-notice>'] = (
        mlist.FormatUmbrellaNotice(user, _("password")))
    replacements['<mm-logout-button>'] = (
        mlist.FormatButton('logout', _('Log out')))
    replacements['<mm-options-submit-button>'] = mlist.FormatButton(
        'options-submit', _('Submit My Changes'))
    replacements['<mm-global-pw-changes-button>'] = (
        CheckBox('pw-globally', 1, checked=0).Format())
    replacements['<mm-global-deliver-button>'] = (
        CheckBox('deliver-globally', 1, checked=0).Format())
    replacements['<mm-global-remind-button>'] = (
        CheckBox('remind-globally', 1, checked=0).Format())

    days = int(mm_cfg.PENDING_REQUEST_LIFE / mm_cfg.days(1))
    if days > 1:
        units = _('days')
    else:
        units = _('day')
    replacements['<mm-pending-days>'] = _('%(days)d %(units)s')

    replacements['<mm-new-address-box>'] = mlist.FormatBox('new-address')
    replacements['<mm-confirm-address-box>'] = mlist.FormatBox(
        'confirm-address')
    replacements['<mm-change-address-button>'] = mlist.FormatButton(
        'change-of-address', _('Change My Address'))
    replacements['<mm-global-change-of-address>'] = CheckBox(
        'changeaddr-globally', 1, checked=0).Format()

    if cpuser is not None:
        replacements['<mm-case-preserved-user>'] = _('''
You are subscribed to this list with the case-preserved address
<em>%(cpuser)s</em>.''')
    else:
        replacements['<mm-case-preserved-user>'] = ''

    doc.AddItem(mlist.ParseTags('options.html', replacements, userlang))



def loginpage(mlist, doc, user, cgidata):
    realname = mlist.real_name
    obuser = Utils.ObscureEmail(user)
    # Set up the login page
    form = Form('%s/%s' % (mlist.GetScriptURL('options'), obuser))
    table = Table(width='100%', border=0, cellspacing=4, cellpadding=5)
    # Set up the title
    title = _('%(realname)s list: member options for user %(user)s')
    doc.SetTitle(title)
    table.AddRow([Center(Header(2, title))])
    table.AddCellInfo(table.GetCurrentRowIndex(), 0,
                      bgcolor=mm_cfg.WEB_HEADER_COLOR)
    # Preamble
    table.AddRow([_("""In order to change your membership option, you must
    first log in by giving your membership password in the section below.  If
    you don't remember your membership password, you can have it emailed to
    you by clicking on the button below.  If you just want to unsubscribe from
    this list, click on the <em>Unsubscribe</em> button and a confirmation
    message will be sent to you.

    <p><strong><em>Important:</em></strong> From this point on, you must have
    cookies enabled in your browser, otherwise none of your changes will take
    effect.

    <p>Session cookies are used in Mailman's membership options interface so
    that you don't need to re-authenticate with every operation.  This cookie
    will expire automatically when you exit your browser, or you can
    explicitly expire the cookie by hitting the <em>Logout</em> link (which
    you'll see once you successfully log in).
    """)])
    # Password and login button
    ptable = Table(width='50%', border=0, cellspacing=4, cellpadding=5)
    ptable.AddRow([Label(_('Password:')),
                   PasswordBox('password', size=20)])
    ptable.AddRow([Center(SubmitButton('login', _('Log in')))])
    ptable.AddCellInfo(ptable.GetCurrentRowIndex(), 0, colspan=2)
    table.AddRow([Center(ptable)])
    # Unsubscribe section, but only if the user didn't just unsubscribe
    if not cgidata.has_key('login-unsub'):
        table.AddRow([Center(Header(2, _('Unsubscribe')))])
        table.AddCellInfo(table.GetCurrentRowIndex(), 0,
                          bgcolor=mm_cfg.WEB_HEADER_COLOR)

        table.AddRow([_("""By clicking on the <em>Unsubscribe</em> button, a
        confirmation message will be emailed to you.  This message will have a
        link that you should click on to complete the removal process (you can
        also confirm by email; see the instructions in the confirmation
        message).""")])

        table.AddRow([Center(SubmitButton('login-unsub', _('Unsubscribe')))])
    # Password reminder section, but only if the user didn't just request a
    # password reminder
    if not cgidata.has_key('login-remind'):
        table.AddRow([Center(Header(2, _('Password reminder')))])
        table.AddCellInfo(table.GetCurrentRowIndex(), 0,
                          bgcolor=mm_cfg.WEB_HEADER_COLOR)

        table.AddRow([_("""By clicking on the <em>Remind</em> button, your
        password will be emailed to you.""")])

        table.AddRow([Center(SubmitButton('login-remind', _('Remind')))])
    # Finish up glomming together the login page
    form.AddItem(table)
    doc.AddItem(form)
    doc.AddItem(mlist.GetMailmanFooter())



def add_error_message(doc, errmsg, tag='Error: ', *args):
    doc.AddItem(Header(3, Bold(FontAttr(
        _(tag), color=mm_cfg.WEB_ERROR_COLOR, size="+2")).Format() +
                       Italic(errmsg % args).Format()))



def lists_of_member(hostname, user):
    onlists = []
    for listname in Utils.list_names():
        mlist = MailList.MailList(listname, lock=0)
        if mlist.host_name <> hostname:
            continue
        if not mlist.IsMember(user):
            continue
        onlists.append(mlist)
    return onlists



def change_password(mlist, user, newpw, confirmpw):
    # This operation requires the list lock, so let's set up the signal
    # handling so the list lock will get released when the user hits the
    # browser stop button.
    def sigterm_handler(signum, frame, mlist=mlist):
        # Make sure the list gets unlocked...
        mlist.Unlock()
        # ...and ensure we exit, otherwise race conditions could cause us to
        # enter MailList.Save() while we're in the unlocked state, and that
        # could be bad!
        sys.exit(0)

    # Must own the list lock!
    mlist.Lock()
    try:
        # Install the emergency shutdown signal handler
        signal.signal(signal.SIGTERM, sigterm_handler)
        # change the user's password
        mlist.ChangeUserPassword(user, newpw, confirmpw)
        mlist.Save()
    finally:
        mlist.Unlock()



def global_options(mlist, user, global_enable, global_remind):
    def sigterm_handler(signum, frame, mlist=mlist):
        # Make sure the list gets unlocked...
        mlist.Unlock()
        # ...and ensure we exit, otherwise race conditions could cause us to
        # enter MailList.Save() while we're in the unlocked state, and that
        # could be bad!
        sys.exit(0)

    # Must own the list lock!
    mlist.Lock()
    try:
        # Install the emergency shutdown signal handler
        signal.signal(signal.SIGTERM, sigterm_handler)

        if global_enable is not None:
            mlist.SetUserOption(user, mm_cfg.DisableDelivery, global_enable)

        if global_remind is not None:
            mlist.SetUserOption(user, mm_cfg.SuppressPasswordReminder,
                                global_remind)

        mlist.Save()
    finally:
        mlist.Unlock()
