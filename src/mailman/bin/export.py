# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

"""Export an XML representation of a mailing list."""

import sys
import codecs
import datetime
import optparse

from xml.sax.saxutils import escape

from mailman import Defaults
from mailman import errors
from mailman import MemberAdaptor
from mailman.MailList import MailList
from mailman.configuration import config
from mailman.core.i18n import _
from mailman.initialize import initialize
from mailman.version import MAILMAN_VERSION


SPACE = ' '

TYPES = {
    Defaults.Toggle         : 'bool',
    Defaults.Radio          : 'radio',
    Defaults.String         : 'string',
    Defaults.Text           : 'text',
    Defaults.Email          : 'email',
    Defaults.EmailList      : 'email_list',
    Defaults.Host           : 'host',
    Defaults.Number         : 'number',
    Defaults.FileUpload     : 'upload',
    Defaults.Select         : 'select',
    Defaults.Topics         : 'topics',
    Defaults.Checkbox       : 'checkbox',
    Defaults.EmailListEx    : 'email_list_ex',
    Defaults.HeaderFilter   : 'header_filter',
    }



class Indenter:
    def __init__(self, fp, indentwidth=4):
        self._fp     = fp
        self._indent = 0
        self._width  = indentwidth

    def indent(self):
        self._indent += 1

    def dedent(self):
        self._indent -= 1
        assert self._indent >= 0

    def write(self, s):
        if s <> '\n':
            self._fp.write(self._indent * self._width * ' ')
        self._fp.write(s)



class XMLDumper(object):
    def __init__(self, fp):
        self._fp        = Indenter(fp)
        self._tagbuffer = None
        self._stack     = []

    def _makeattrs(self, tagattrs):
        # The attribute values might contain angle brackets.  They might also
        # be None.
        attrs = []
        for k, v in tagattrs.items():
            if v is None:
                v = ''
            else:
                v = escape(str(v))
            attrs.append('%s="%s"' % (k, v))
        return SPACE.join(attrs)

    def _flush(self, more=True):
        if not self._tagbuffer:
            return
        name, attributes = self._tagbuffer
        self._tagbuffer = None
        if attributes:
            attrstr = ' ' + self._makeattrs(attributes)
        else:
            attrstr = ''
        if more:
            print >> self._fp, '<%s%s>' % (name, attrstr)
            self._fp.indent()
            self._stack.append(name)
        else:
            print >> self._fp, '<%s%s/>' % (name, attrstr)

    # Use this method when you know you have sub-elements.
    def _push_element(self, _name, **_tagattrs):
        self._flush()
        self._tagbuffer = (_name, _tagattrs)

    def _pop_element(self, _name):
        buffered = bool(self._tagbuffer)
        self._flush(more=False)
        if not buffered:
            name = self._stack.pop()
            assert name == _name, 'got: %s, expected: %s' % (_name, name)
            self._fp.dedent()
            print >> self._fp, '</%s>' % name

    # Use this method when you do not have sub-elements
    def _element(self, _name, _value=None, **_attributes):
        self._flush()
        if _attributes:
            attrs = ' ' + self._makeattrs(_attributes)
        else:
            attrs = ''
        if _value is None:
            print >> self._fp, '<%s%s/>' % (_name, attrs)
        else:
            # The value might contain angle brackets.
            value = escape(unicode(_value))
            print >> self._fp, '<%s%s>%s</%s>' % (_name, attrs, value, _name)

    def _do_list_categories(self, mlist, k, subcat=None):
        info = mlist.GetConfigInfo(k, subcat)
        label, gui = mlist.GetConfigCategories()[k]
        if info is None:
            return
        for data in info[1:]:
            if not isinstance(data, tuple):
                continue
            varname = data[0]
            # Variable could be volatile
            if varname.startswith('_'):
                continue
            vtype = data[1]
            # Munge the value based on its type
            value = None
            if hasattr(gui, 'getValue'):
                value = gui.getValue(mlist, vtype, varname, data[2])
            if value is None:
                value = getattr(mlist, varname)
            widget_type = TYPES[vtype]
            if isinstance(value, list):
                self._push_element('option', name=varname, type=widget_type)
                for v in value:
                    self._element('value', v)
                self._pop_element('option')
            else:
                self._element('option', value, name=varname, type=widget_type)

    def _dump_list(self, mlist):
        # Write list configuration values
        self._push_element('list', name=mlist.fqdn_listname)
        self._push_element('configuration')
        self._element('option',
                      mlist.preferred_language,
                      name='preferred_language')
        for k in config.ADMIN_CATEGORIES:
            subcats = mlist.GetConfigSubCategories(k)
            if subcats is None:
                self._do_list_categories(mlist, k)
            else:
                for subcat in [t[0] for t in subcats]:
                    self._do_list_categories(mlist, k, subcat)
        self._pop_element('configuration')
        # Write membership
        self._push_element('roster')
        digesters = set(mlist.getDigestMemberKeys())
        for member in sorted(mlist.getMembers()):
            attrs = dict(id=member)
            cased = mlist.getMemberCPAddress(member)
            if cased <> member:
                attrs['original'] = cased
            self._push_element('member', **attrs)
            self._element('realname', mlist.getMemberName(member))
            self._element('password', mlist.getMemberPassword(member))
            self._element('language', mlist.getMemberLanguage(member))
            # Delivery status, combined with the type of delivery
            attrs = {}
            status = mlist.getDeliveryStatus(member)
            if status == MemberAdaptor.ENABLED:
                attrs['status'] = 'enabled'
            else:
                attrs['status'] = 'disabled'
                attrs['reason'] = {MemberAdaptor.BYUSER    : 'byuser',
                                   MemberAdaptor.BYADMIN   : 'byadmin',
                                   MemberAdaptor.BYBOUNCE  : 'bybounce',
                                   }.get(mlist.getDeliveryStatus(member),
                                         'unknown')
            if member in digesters:
                if mlist.getMemberOption(member, Defaults.DisableMime):
                    attrs['delivery'] = 'plain'
                else:
                    attrs['delivery'] = 'mime'
            else:
                attrs['delivery'] = 'regular'
            changed = mlist.getDeliveryStatusChangeTime(member)
            if changed:
                when = datetime.datetime.fromtimestamp(changed)
                attrs['changed'] = when.isoformat()
            self._element('delivery', **attrs)
            for option, flag in Defaults.OPTINFO.items():
                # Digest/Regular delivery flag must be handled separately
                if option in ('digest', 'plain'):
                    continue
                value = mlist.getMemberOption(member, flag)
                self._element(option, value)
            topics = mlist.getMemberTopics(member)
            if not topics:
                self._element('topics')
            else:
                self._push_element('topics')
                for topic in topics:
                    self._element('topic', topic)
                self._pop_element('topics')
            self._pop_element('member')
        self._pop_element('roster')
        self._pop_element('list')

    def dump(self, listnames):
        print >> self._fp, '<?xml version="1.0" encoding="UTF-8"?>'
        self._push_element('mailman', **{
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:noNamespaceSchemaLocation': 'ssi-1.0.xsd',
            })
        for listname in sorted(listnames):
            try:
                mlist = MailList(listname, lock=False)
            except errors.MMUnknownListError:
                print >> sys.stderr, _('No such list: $listname')
                continue
            self._dump_list(mlist)
        self._pop_element('mailman')

    def close(self):
        while self._stack:
            self._pop_element()



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Export the configuration and members of a mailing list in XML format."""))
    parser.add_option('-o', '--outputfile',
                      metavar='FILENAME', default=None, type='string',
                      help=_("""\
Output XML to FILENAME.  If not given, or if FILENAME is '-', standard out is
used."""))
    parser.add_option('-l', '--listname',
                      default=[], action='append', type='string',
                      metavar='LISTNAME', dest='listnames', help=_("""\
The list to include in the output.  If not given, then all mailing lists are
included in the XML output.  Multiple -l flags may be given."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        parser.error(_('Unexpected arguments'))
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    close = False
    if opts.outputfile in (None, '-'):
        writer = codecs.getwriter('utf-8')
        fp = writer(sys.stdout)
    else:
        fp = codecs.open(opts.outputfile, 'w', 'utf-8')
        close = True

    try:
        dumper = XMLDumper(fp)
        if opts.listnames:
            listnames = []
            for listname in opts.listnames:
                if '@' not in listname:
                    listname = '%s@%s' % (listname, config.DEFAULT_EMAIL_HOST)
                listnames.append(listname)
        else:
            listnames = config.list_manager.names
        dumper.dump(listnames)
        dumper.close()
    finally:
        if close:
            fp.close()
