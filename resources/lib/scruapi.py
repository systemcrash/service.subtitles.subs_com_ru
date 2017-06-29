# -*- coding: utf-8 -*-


"""
The SCRu API interface.
"""

import re
from contextlib import closing
from json import loads
from urllib import quote_plus
from urllib2 import urlopen

class SCRuAPI:
    """
    The SCRu API.
    """

    def __init__(self):
        self.logger = None
        self._base_url = u'http://subs.com.ru'

    def search(self, title, year):
        """
        Search for a movie.

        :param title: Movie title
        :type title: unicode
        :param year: Year of release
        :type year: int
        :return: Download page URL
        :rtype: unicode
        """

        self.logger.debug(u'Looking for {0} ({1})'.format(title, year))

        """url = u'{0}/?t={1}&y={2}'.format(self._base_url, quote_plus(title), year)"""
        url = u'{0}/index.php?e=search&sq={1}'.format(self._base_url, quote_plus(title))

        with closing(urlopen(url)) as f:
            response = f.read().decode('string-escape').decode("utf-8")

        #self.logger.debug(response)

        # if not response.get('Response', u'False') == u'True':
        #     self.logger.debug(u'Sumtinwong')

        pattern = re.compile(r'(\<h4\>Ошибка\<\/h4\>)', re.UNICODE)
        match = pattern.search(response)
        if match:
            self.logger.warn(u'No match found for {0} ({1})'.format(title, year))
            return None

        # if isinstance(self._no_results(response), unicode ):
        #     self.logger.warn(u'No match found for {0} ({1})'.format(title, year))
        #     return None

        '''imdb_id = response['imdbID']'''
        '''self.logger.debug(u'IMDB identifier {2} found for {0} ({1})'.format(title, year, imdb_id))'''

        '''return imdb_id'''
        self.logger.debug(u'Download page acquired for search string \"{0}\" and year ({1})'.format(title, year))
        #self.logger.debug(u'response HTML:' + response )
        self.logger.debug(u'\n')

        subsearch = self._search_within_results(response, year)

        if subsearch is None:
            #bail
            self.logger.info(u'No subtitles found for the title \"{0}\" and year ({1})'.format(title, year))
            return [None, None]
        else:
            #potential error here
            downloadpageurl = u'{0}/{1}'.format(self._base_url, subsearch )
            self.logger.debug(u'Download page URL: {0}'.format(downloadpageurl) )
            with closing( urlopen(downloadpageurl) ) as resultf:
                response = resultf.read().decode('string-escape').decode("utf-8")
                #self.logger.debug(u'response HTML:' + response )
                return [response, downloadpageurl]




    # @staticmethod
    # def _no_results(html_results):
    #     pattern = re.compile(r'(\<h4\>Ошибка\<\/h4\>)', re.UNICODE)
    #     match = pattern.search(html_results)
    #     return unicode(match.group(1)) if match else None
    #     #return match

    @staticmethod
    def _search_within_results(page, year):
        """Get the subtitle archive URL from the subtitle page.

        :param page: Film search results page
        :type page: unicode
        :return: Subtitle URL
        :rtype: unicode
        """

        pattern = re.compile(r'a href="(page.php\?id=[0-9]*)\&.*[\s].*[\s].*[0-9]{2}\/[0-9]{2}\/('+year+')', re.UNICODE)
        match = pattern.search(page)
        return unicode(match.group(1)) if match else None



