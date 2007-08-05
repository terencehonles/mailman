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

"""Interfaces for list styles."""

from zope.interface import Interface, Attribute



class IStyle(Interface):
    """Application of a style to an existing mailing list."""

    name = Attribute(
        """The name of this style.  Must be unique.""")

    priority = Attribute(
        """The priority of this style, as an integer.""")

    def apply(mailing_list):
        """Apply the style to the mailing list.

        :param mailing_list: an IMailingList.
        """

    def match(mailing_list, styles):
        """Give this list a chance to match the mailing list.

        If the style's internal matching rules match the `mailing_list`, then
        the style may append itself to the `styles` list.  This list will be
        ordered when returned from `IStyleManager.lookup()`.

        :param mailing_list: an IMailingList.
        :param styles: ordered list of IStyles matched so far.
        """



class IStyleManager(Interface):
    """A manager of styles and style chains."""

    def get(name):
        """Return the named style or None.

        :param name: A style name.
        :return: an IStyle or None.
        """

    def lookup(mailing_list):
        """Return a list of styles for the given mailing list.

        Use various registered rules to find an IStyle for the given mailing
        list.  The returned styles are ordered by their priority.

        Style matches can be registered and reordered by plugins.

        :param mailing_list: An IMailingList.
        :return: ordered list of IStyles.  Zero is the lowest priority.
        """

    styles = Attribute(
        """An iterator over all the styles known by this manager.

        Styles are ordered by their priority, which may be changed.
        """)

    def register(style):
        """Register a style with this manager.

        :param style: an IStyle.
        :raises DuplicateStyleError: if a style with the same name was already
            registered.
        """

    def unregister(style):
        """Unregister the style.

        :param style: an IStyle.
        :raises KeyError: If the style's name is not currently registered.
        """
