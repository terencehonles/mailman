# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
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

"""Import the XML representation of a mailing list."""

import sys
import codecs
import optparse
import traceback

from xml.dom import minidom
from xml.parsers.expat import ExpatError

from mailman import Defaults
from mailman import MemberAdaptor
from mailman import Utils
from mailman import passwords
from mailman.MailList import MailList
from mailman.core.i18n import _
from mailman.initialize import initialize
from mailman.interfaces.domain import BadDomainSpecificationError
from mailman.version import MAILMAN_VERSION


OPTS = None



def nodetext(node):
    # Expect only one TEXT_NODE in the list of children
    for child in node.childNodes:
        if child.nodeType == node.TEXT_NODE:
            return child.data
    return u''


def nodegen(node, *elements):
    for child in node.childNodes:
        if child.nodeType <> minidom.Node.ELEMENT_NODE:
            continue
        if elements and child.tagName not in elements:
            print _('Ignoring unexpected element: $node.tagName')
        else:
            yield child



def parse_config(node):
    config = dict()
    for child in nodegen(node, 'option'):
        name  = child.getAttribute('name')
        if not name:
            print _('Skipping unnamed option')
            continue
        vtype = child.getAttribute('type') or 'string'
        if vtype in ('email_list', 'email_list_ex', 'checkbox'):
            value = []
            for subnode in nodegen(child):
                value.append(nodetext(subnode))
        elif vtype == 'bool':
            value = nodetext(child)
            try:
                value = bool(int(value))
            except ValueError:
                value = {'true' : True,
                         'false': False,
                         }.get(value.lower())
                if value is None:
                    print _('Skipping bad boolean value: $value')
                    continue
        elif vtype == 'radio':
            value = nodetext(child).lower()
            boolval = {'true' : True,
                       'false': False,
                       }.get(value)
            if boolval is None:
                value = int(value)
            else:
                value = boolval
        elif vtype == 'number':
            value = nodetext(child)
            # First try int then float
            try:
                value = int(value)
            except ValueError:
                value = float(value)
        elif vtype in ('header_filter', 'topics'):
            value = []
            fakebltins = dict(__builtins__ = dict(True=True, False=False))
            for subnode in nodegen(child):
                reprstr  = nodetext(subnode)
                # Turn the reprs back into tuples, in a safe way
                tupleval = eval(reprstr, fakebltins)
                value.append(tupleval)
        else:
            value = nodetext(child)
        # And now some special casing :(
        if name == 'new_member_options':
            value = int(nodetext(child))
        config[name] = value
    return config




def parse_roster(node):
    members = []
    for child in nodegen(node, 'member'):
        member = dict()
        member['id'] = mid = child.getAttribute('id')
        if not mid:
            print _('Skipping member with no id')
            continue
        if OPTS.verbose:
            print _('* Processing member: $mid')
        for subnode in nodegen(child):
            attr = subnode.tagName
            if attr == 'delivery':
                value = (subnode.getAttribute('status'),
                         subnode.getAttribute('delivery'))
            elif attr in ('hide', 'ack', 'notmetoo', 'nodupes', 'nomail'):
                value = {'true' : True,
                         'false': False,
                         }.get(nodetext(subnode).lower(), False)
            elif attr == 'topics':
                value = []
                for subsubnode in nodegen(subnode):
                    value.append(nodetext(subsubnode))
            elif attr == 'password':
                value = nodetext(subnode)
                if OPTS.reset_passwords or value == '{NONE}' or not value:
                    value = passwords.make_secret(Utils.MakeRandomPassword())
            else:
                value = nodetext(subnode)
            member[attr] = value
        members.append(member)
    return members



def load(fp):
    try:
        doc = minidom.parse(fp)
    except ExpatError:
        print _('Expat error in file: $fp.name')
        traceback.print_exc()
        sys.exit(1)
    doc.normalize()
    # Make sure there's only one top-level <mailman> node
    gen = nodegen(doc, 'mailman')
    top = gen.next()
    try:
        gen.next()
    except StopIteration:
        pass
    else:
        print _('Malformed XML; duplicate <mailman> nodes')
        sys.exit(1)
    all_listdata = []
    for listnode in nodegen(top, 'list'):
        listdata = dict()
        name = listnode.getAttribute('name')
        if OPTS.verbose:
            print _('Processing list: $name')
        if not name:
            print _('Ignoring malformed <list> node')
            continue
        for child in nodegen(listnode, 'configuration', 'roster'):
            if child.tagName == 'configuration':
                list_config = parse_config(child)
            else:
                assert(child.tagName == 'roster')
                list_roster = parse_roster(child)
        all_listdata.append((name, list_config, list_roster))
    return all_listdata



def create(all_listdata):
    for name, list_config, list_roster in all_listdata:
        fqdn_listname = '%s@%s' % (name, list_config['host_name'])
        if Utils.list_exists(fqdn_listname):
            print _('Skipping already existing list: $fqdn_listname')
            continue
        mlist = MailList()
        try:
            if OPTS.verbose:
                print _('Creating mailing list: $fqdn_listname')
            mlist.Create(fqdn_listname, list_config['owner'][0],
                         list_config['password'])
        except BadDomainSpecificationError:
            print _('List is not in a supported domain: $fqdn_listname')
            continue
        # Save the list creation, then unlock and relock the list.  This is so
        # that we use normal SQLAlchemy transactions to manage all the
        # attribute and membership updates.  Without this, no transaction will
        # get committed in the second Save() below and we'll lose all our
        # updates.
        mlist.Save()
        mlist.Unlock()
        mlist.Lock()
        try:
            for option, value in list_config.items():
                # XXX Here's what sucks.  Some properties need to have
                # _setValue() called on the gui component, because those
                # methods do some pre-processing on the values before they're
                # applied to the MailList instance.  But we don't have a good
                # way to find a category and sub-category that a particular
                # property belongs to.  Plus this will probably change.  So
                # for now, we'll just hard code the extra post-processing
                # here.  The good news is that not all _setValue() munging
                # needs to be done -- for example, we've already converted
                # everything to dollar strings.
                if option in ('filter_mime_types', 'pass_mime_types',
                              'filter_filename_extensions',
                              'pass_filename_extensions'):
                    value = value.splitlines()
                if option == 'available_languages':
                    mlist.os(*value)
                else:
                    setattr(mlist, option, value)
            for member in list_roster:
                mid = member['id']
                if OPTS.verbose:
                    print _('* Adding member: $mid')
                status, delivery = member['delivery']
                kws = {'password'   : member['password'],
                       'language'   : member['language'],
                       'realname'   : member['realname'],
                       'digest'     : delivery <> 'regular',
                       }
                mlist.addNewMember(mid, **kws)
                status = {'enabled'     : MemberAdaptor.ENABLED,
                          'byuser'      : MemberAdaptor.BYUSER,
                          'byadmin'     : MemberAdaptor.BYADMIN,
                          'bybounce'    : MemberAdaptor.BYBOUNCE,
                          }.get(status, MemberAdaptor.UNKNOWN)
                mlist.setDeliveryStatus(mid, status)
                for opt in ('hide', 'ack', 'notmetoo', 'nodupes', 'nomail'):
                    mlist.setMemberOption(mid,
                                          Defaults.OPTINFO[opt],
                                          member[opt])
                topics = member.get('topics')
                if topics:
                    mlist.setMemberTopics(mid, topics)
            mlist.Save()
        finally:
            mlist.Unlock()



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Import the configuration and/or members of a mailing list in XML format.  The
imported mailing list must not already exist.  All mailing lists named in the
XML file are imported, but those that already exist are skipped unless --error
is given."""))
    parser.add_option('-i', '--inputfile',
                      metavar='FILENAME', default=None, type='string',
                      help=_("""\
Input XML from FILENAME.  If not given, or if FILENAME is '-', standard input
is used."""))
    parser.add_option('-p', '--reset-passwords',
                      default=False, action='store_true', help=_("""\
With this option, user passwords in the XML are ignored and are reset to a
random password.  If the generated passwords were not included in the input
XML, they will always be randomly generated."""))
    parser.add_option('-v', '--verbose',
                      default=False, action='store_true',
                      help=_('Produce more verbose output'))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        parser.error(_('Unexpected arguments'))
    return parser, opts, args



def main():
    global OPTS

    parser, opts, args = parseargs()
    initialize(opts.config)
    OPTS = opts

    if opts.inputfile in (None, '-'):
        fp = sys.stdin
    else:
        fp = open(opts.inputfile, 'r')

    try:
        listbags = load(fp)
        create(listbags)
    finally:
        if fp is not sys.stdin:
            fp.close()
