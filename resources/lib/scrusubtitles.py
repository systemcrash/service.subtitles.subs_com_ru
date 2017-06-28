# -*- coding: utf-8 -*-


"""
SCRu Subtitles website interface.
"""


from StringIO import StringIO
from io import BytesIO
from abc import abstractmethod, ABCMeta
from contextlib import closing
from urllib2 import urlopen
from urllib2 import Request
import cookielib
import urllib2
from rarfile import RarFile
import re
import os


class SCRuSubtitlesLogger:
    """Abstract logger."""

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def debug(self, message):
        """Print a debug message.

        :param message: Message
        :type message: unicode
        """

    @abstractmethod
    def info(self, message):
        """Print an informative message.

        :param message: Message
        :type message: unicode
        """

    @abstractmethod
    def warn(self, message):
        """Print a warning message.

        :param message: Message
        :type message: unicode
        """

    @abstractmethod
    def error(self, message):
        """Print an error message.

        :param message: Message
        :type message: unicode
        """


class SCRuSubtitlesListener:
    """Abstract SCRu Subtitles event listener."""

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def on_subtitle_found(self, subtitle, referer):
        """Event handler called when a matching subtitle has been found.

        :param subtitle: Subtitle details
        :type subtitle: dict of [str, unicode]
        """

    @abstractmethod
    def on_subtitle_downloaded(self, path):
        """Event handler called when a subtitle has been downloaded and unpacked.

        :param path: Subtitle path
        :type path: unicode
        """


class SCRuSubtitles:
    """SCRu Subtitles access class."""

    _extensions = ('.ass', '.smi', '.srt', '.ssa', '.sub', '.txt')

    def __init__(self):
        self.listener = None
        """:type: ScruSubtitlesListener"""

        self.logger = None
        """:type: ScruSubtitlesLogger"""

        self.workdir = None
        """:type: unicode"""

        self._base_url = u'http://subs.com.ru'

        self._download_param = u'&a=dl'

        self.cookies = cookielib.LWPCookieJar()
        self.handlers = [
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
            urllib2.HTTPCookieProcessor(self.cookies)
            ]
        self.opener = urllib2.build_opener(*self.handlers)


    def fetch(self, uri):
        req = urllib2.Request(uri)
        return self.opener.open(req)

    def getcookie(self):
        for cookie in self.cookies:
            if 'PHPSESSID' in cookie.name:
                return cookie.value


    def download(self, url, filename):
        """Download a subtitle.

        The on_subtitle_download() method of the registered listener will be called for each downloaded subtitle.

        :param url: URL to subtitle archive
        :type url: unicode
        :param filename: Path to subtitle file within the archive
        :type filename: unicode
        """

        # referer = urllib2.unquote(url)
        # self.logger.debug(u'Got referer URI: {0}'.format(referer))

        # self.fetch(referer)
        # cookie = self.getcookie()
        # self.logger.debug(u'Got session cookie: {0}'.format(cookie))
        # req = Request(referer + self._download_param)
        # req.add_header('Cookie', 'PHPSESSID=' + cookie)

        path = os.path.join(self.workdir, os.path.basename(filename))

        # self.logger.debug(u'Downloading subtitle archive from {0}'.format(referer + self._download_param))
        self.logger.debug(u'Downloading URL: {0}'.format( urllib2.unquote(url) ) )

        with closing(urlopen( urllib2.unquote(url) )) as f:
            content = StringIO(f.read())

        self.logger.debug(u'Extracting subtitle to {0}'.format(path))
        with RarFile(content) as z, closing(open(path.encode('utf-8'), mode='wb')) as f:
            f.write(z.read(filename).decode('windows-1251').encode('utf-8'))

        self.listener.on_subtitle_downloaded(path)

    def search(self, page, referer, languages):
        """Get subtitle download.

        The on_subtitle_found() method of the registered listener will be called for each found subtitle.

        :param page: Search match page HTML
        :type imdb_id: unicode
        :param languages: Accepted languages
        :type languages: list of unicode
        """
        self.logger.debug(u'Acquiring download link from download page')

        archive_filename = self._get_subtitle_archive_filename(page)

        download_referer = referer

        self._list_subtitles_archive({
                    # 'language': language,
                    # 'rating': rating,
                    'referer' : download_referer,
                    'url': archive_filename,
                })

    def _fetch_subtitle_page(self, link):
        """Fetch a subtitle page.

        :param link: Relative URL to subtitle page
        :type link: unicode
        :return: Subtitle page
        :rtype: unicode
        """

        url = '{0}{1}'.format(self._base_url, link)
        self.logger.debug('Fetching subtitle page from {0}'.format(url))

        with closing(urlopen(url)) as page:
            encoding = page.info().getparam('charset')
            return unicode(page.read(), encoding)

    def _list_subtitles(self, page, languages):
        """List subtitles from the movie page.

        :param page: Movie page
        :type page: unicode
        :param languages: Accepted languages
        :type languages: list of unicode
        """

        pattern = re.compile(r'<li data-id=".*?"(?: class="((?:high|low)-rating)")?>\s*'
                             r'<span class="rating">\s*(?:<span.*?>.*?</span>\s*)*</span>\s*'
                             r'<a class="subtitle-page" href="(.*?)">\s*'
                             r'<span class="flag flag-.*?">.*?</span>\s*'
                             r'<span>(.*?)</span>.*?'
                             r'<span class="subdesc">.*?</span>\s*'
                             r'(?:<span class="verified-subtitle" title="verified">.*?</span>\s*)?'
                             r'</a>'
                             r'.*?'
                             r'</li>',
                             re.UNICODE)

        for match in pattern.findall(page):
            language = self._get_subtitle_language(unicode(match[2]))
            page_url = unicode(match[1])
            # rating = self._get_subtitle_rating(unicode(match[0]))

            if language in languages:
                page = self._fetch_subtitle_page(page_url)
                subtitle_url = self._get_subtitle_archive_filename(page)

                self._list_subtitles_archive({
                    'language': language,
                    # 'rating': rating,
                    'url': subtitle_url,
                })

            else:
                self.logger.debug(u'Ignoring {0} subtitle {1}'.format(language, page_url))

    def _list_subtitles_archive(self, archive):
        """List subtitles from a RAR archive.

        :param archive: RAR archive URL
        :type archive: dict of [str, unicode]
        """

        self.logger.debug(u'Got referer URL: {0}'.format( archive['referer'] ))
        referer = archive['referer'] + self._download_param

        response = self.fetch(referer)
        cookie = self.getcookie()
        #self.logger.debug(u'Got session cookie: {0}'.format(cookie))
        req = Request(archive['referer'] + self._download_param)
        req.add_header('Cookie', 'PHPSESSID=' +cookie)
        #self.logger.debug(u'Got URL: {0}'.format(archive['referer'] + self._download_param ))
        # parse URL a second time with cookie to get download link
        response = self.fetch( referer )
        # response.geturl() #download link

        download_uri = response.geturl()
        response.close()

        with closing(urlopen( download_uri )) as f:
            content = StringIO(f.read())

        #self.logger.debug(u'Got archive: {0}')

        with RarFile(content) as f:
            filenames = [
                filename for filename in f.namelist()
                if filename.endswith(self._extensions) and not os.path.basename(filename).startswith('.')
            ]

        for filename in filenames:
            self.logger.debug(u'Found 1 subtitle at {0}: {1}'.format(archive['referer'], filename))
            self.listener.on_subtitle_found({
                'filename': filename,
                # 'language': archive['language'],
                # 'rating': archive['rating'],
                'url': archive['url'],
                'referer': archive['referer'],
                'download_uri': download_uri
            })

    @staticmethod
    def _get_subtitle_language(language):
        """Get the Kodi english name for a SCRu subtitle language.

        :param language: Subtitle language
        :type language: unicode
        :return: Kodi language
        :rtype: unicode
        """

        return {
            u'Russian': u'Russian',
            u'English': u'English',
        }.get(language, language)

    # @staticmethod
    # def _get_subtitle_rating(rating):
    #     """Get Kodi subtitle rating.

    #     :param rating: Subtitles rating
    #     :type rating: unicode
    #     :return: Subtitles rating
    #     :rtype: unicode
    #     """

    #     return {
    #         u'high-rating': u'5',
    #         u'low-rating': u'0',
    #     }.get(rating, u'3')

    @staticmethod
    def _get_subtitle_archive_filename(page):
        """Get the subtitle archive URL from the subtitle page.

        :param page: Subtitle page
        :type page: unicode
        :return: Subtitle URL
        :rtype: unicode
        """
        #works for matching download links, but requires referer and cookie etc.
        #pattern = re.compile(r'<a href="([^"]*a=dl)" title="[^"]*">', re.UNICODE)
        pattern = re.compile(r'<td class="even">(.*.rar)</td>',re.UNICODE)
        match = pattern.search(page)
        return unicode(match.group(1)) if match else None
