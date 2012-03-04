# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""Template finder."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TemplateFinder',
    ]


import os

from restish import http, resource

from mailman.config import config
from mailman.utilities.i18n import TemplateNotFoundError, find


# Use mimetypes.guess_all_extensions()?
EXTENSIONS = {
    'text/plain': '.txt',
    'text/html': '.html',
    }



class TemplateFinder(resource.Resource):
    """Template finder resource."""

    def __init__(self, mlist, template, language, content_type):
        self.mlist = mlist
        self.template = template
        self.language = language
        self.content_type = content_type

    @resource.GET()
    def find_template(self, request):
        # XXX We currently only support .txt and .html files.
        extension = EXTENSIONS.get(self.content_type)
        if extension is None:
            return http.not_found()
        template = self.template + extension
        fp = None
        try:
            try:
                path, fp = find(template, self.mlist, self.language)
            except TemplateNotFoundError:
                return http.not_found()
            else:
                return fp.read()
        finally:
            if fp is not None:
                fp.close()
