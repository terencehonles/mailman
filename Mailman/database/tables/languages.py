# Copyright (C) 2007 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Available languages table."""

from sqlalchemy import *



class Language(object):
    def __init__(self, code):
        self.code = code

    def __repr__(self):
        return u'<Language "%s">' % self.code

    def __unicode__(self):
        return self.code

    __str__ = __unicode__



def make_table(metadata, tables):
    language_table = Table(
        'Languages', metadata,
        # Two letter language code
        Column('language_id',   Integer, primary_key=True),
        Column('code',          Unicode),
        )
    # Associate List
    available_languages_table = Table(
        'AvailableLanguages', metadata,
        Column('list_id',       Integer, ForeignKey('Listdata.list_id')),
        Column('language_id',   Integer, ForeignKey('Languages.language_id')),
        )
    mapper(Language, language_table)
    tables.bind(language_table)
    tables.bind(available_languages_table, 'available_languages')
