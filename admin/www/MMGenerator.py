"""Generator for the Mailman on-line documentation.

Requires ht2html.py, available from

http://www.wooz.org/users/barry/software/pyware.html
"""

import os

from Skeleton import Skeleton
from Sidebar import Sidebar, BLANKCELL
from Banner import Banner
from HTParser import HTParser
from LinkFixer import LinkFixer



sitelinks = [
    # Row 1
    ('%(rootdir)s/index.html',  'Home'),
    ('%(rootdir)s/users.html',  'Users'),
    ('http://www.list.org/',    'List.Org'),
    # Row 2
    ('%(rootdir)s/install-start.html',                   'Installation'),
    ('%(rootdir)s/mgrs.html',                            'List Managers'),
    ('http://www.gnu.org/software/mailman/mailman.html', 'Mailman at GNU'),
    # Row 3
    ('%(rootdir)s/faq.html',    'FAQ'),
    ('%(rootdir)s/admins.html', 'Site Administrators'),
    ('http://www.python.org/',  'Python.Org'),
    # Row 4
    ('%(rootdir)s/lists.html',  'Discussion Lists'),
    ('%(rootdir)s/devs.html',   'Developers'),
    ('http://www.gnu.org/',     'Gnu.Org'),
    ]



class MMGenerator(Skeleton, Sidebar, Banner):
    def __init__(self, file, rootdir, relthis):
        self.__body = None
        root, ext = os.path.splitext(file)
        html = root + '.html'
        p = self.__parser = HTParser(file, 'mailman-users@python.org')
        f = self.__linkfixer = LinkFixer(html, rootdir, relthis)
        p.process_sidebar()
        p.sidebar.append(BLANKCELL)
        # massage our links
        self.__d = {'rootdir': rootdir}
        self.__linkfixer.massage(p.sidebar, self.__d)
        # tweak
        p.sidebar.append(('http://www.python.org/', '''
<center>
    <img border=0 src="%(rootdir)s/images/PythonPoweredSmall.png"></center>'''
                           % self.__d))
        p.sidebar.append(BLANKCELL)
        copyright = self.__parser.get('copyright', '1998,1999,2000')
        p.sidebar.append((None, '&copy; ' + copyright))
        p.sidebar.append((None, 'Free Software Foundation, Inc.'))
        Sidebar.__init__(self, p.sidebar)
        #
        # fix up our site links, no relthis because the site links are
        # relative to the root of my web pages
        #
        sitelink_fixer = LinkFixer(f.myurl(), rootdir)
        sitelink_fixer.massage(sitelinks, self.__d, aboves=1)
        Banner.__init__(self, sitelinks, cols=3)
        # kludge!
##        for i in range(len(p.sidebar)-1, -1, -1):
##            if p.sidebar[i] == 'Email Us':
##                p.sidebar[i] = 'Email me'
##                break

    def get_corner(self):
        rootdir = self.__linkfixer.rootdir()
        return '''
<center>
    <a href="%(rootdir)s/index.html">
    <img border=0 src="%(rootdir)s/images/logo-70.jpg"></a></center>''' \
    % self.__d

    def get_corner_bgcolor(self):
        return 'black'

    def get_banner(self):
        return Banner.get_banner(self)

    def get_title(self):
        return self.__parser.get('title')

    def get_sidebar(self):
        return Sidebar.get_sidebar(self)

    def get_banner_attributes(self):
        return 'CELLSPACING=0 CELLPADDING=0'

    def get_body(self):
        if self.__body is None:
            self.__body = self.__parser.fp.read()
        return self.__body

    def get_lightshade(self):
        """Return lightest of 3 color scheme shade."""
        return '#99997c'

    def get_darkshade(self):
        """Return darkest of 3 color scheme shade."""
        return '#663300'
