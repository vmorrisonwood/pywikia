# -*- coding: utf-8 -*-
"""
Script to resolve double redirects, and to delete broken redirects. Requires
access to MediaWiki's maintenance pages or to a XML dump file. Delete
function requires adminship.

Syntax:

    python redirect.py action [-arguments ...]

where action can be one of these:

double         Fix redirects which point to other redirects
broken         Delete redirects where targets don\'t exist. Requires adminship.
both           Both of the above. Permitted only with -api. Implies -api.

and arguments can be:

-xml           Retrieve information from a local XML dump
               (http://download.wikimedia.org). Argument can also be given as
               "-xml:filename.xml". Cannot be used with -api or -moves.
               If neither of -xml -api -moves is given, info will be loaded
               from a special page of the live wiki.

-api           Retrieve information from the wiki via MediaWikis application
               program interface (API). Cannot be used with -xml or -moves.
               If neither of -xml -api -moves is given, info will be loaded
               from a special page of the live wiki.

-moves         Use the page move log to find double-redirect candidates. Only
               works with action "double", does not work with either -xml, or
               -api. If neither of -xml -api -moves is given, info will be
               loaded from a special page of the live wiki.

-namespace:n   Namespace to process. Works only with an XML dump, or the API
               interface. Can be given multiple times, for several namespaces.
               If omitted, with -xml all namespaces are treated, with -api
               only the main (article) namespace is treated.

-offset:n      With -xml, the number of the redirect to restart with (see
               progress). With -moves, the number of hours ago to start
               scanning moved pages. Otherwise, ignored.

-start:title   With -api, the starting page title in each namespace.
               Otherwise ignored. Page needs not exist.

-until:title   With -api, the possible last page title in each namespace.
               Otherwise ignored. Page needs not exist.

-number:n      With -api, the maximum count of redirects to work upon.
               Otherwise ignored. Use 0 for unlimited

-always        Don't prompt you for each replacement.

"""
#
# (C) Daniel Herding, 2004.
#     Purodha Blissenbach, 2009.
#
# Distributed under the terms of the MIT license.
#
#
from __future__ import generators
import wikipedia, config, query
import xmlreader
import re, sys

__version__='$Id$'

# Summary message for fixing double redirects
msg_double={
    'als':u'Bötli: Uflösig vun de doppleti Wyterleitig zue %s',
    'ar': u'روبوت: تصليح تحويلة مزدوجة → %s',
    'bat-smg': u'Robots: Taisuoms dvėgobs paradresavėms → %s',
    'be-x-old': u'Робат: выпраўленьне падвойнага перанакіраваньня → %s',
    'br': u'Kempennet adkas doubl gant robot → %s',
    'cs': u'Robot opravil dvojité přesměrování → %s',
    'de': u'Bot: Korrigiere doppelte Weiterleitung zu %s',
    'en': u'Robot: Fixing double redirect to %s',
    'es': u'Robot: Arreglando doble redirección → %s',
    'fa': u'ربات:اصلاح تغییر مسیر دوتایی → %s',
    'fi': u'Botti korjasi kaksinkertaisen ohjauksen → %s',
    'fr': u'Robot: répare double redirection à %s',
    'ga': u'Róbó: Ag socrú athsheolta dúbailte → %s',
    'he': u'בוט: מתקן הפניה כפולה → %s',
    'hr': u'Bot: Popravak dvostrukih preusmjeravanja → %s',
    'ia': u'Robot: reparation de duple redirection → %s',
    'is': u'Vélmenni: Lagfæri tvöfalda tilvísun → %s',
    'it': u'Bot: Sistemo i redirect doppi a %s',
    'ja': u'ロボットによる: 二重リダイレクト修正 → %s',
    'ka': u'რობოტი: ორმაგი გადამისამართების გასწორება → %s',
    'ko': u'로봇: 이중 넘겨주기 수정 → %s',
    'kk': u'Бот: Шынжырлы айдатуды түзетті → %s',
    'ksh':u'Bot: [[special:doubleredirects|Dubbel Ömlëijdong]] fottjemaat → %s',
    'lb': u'Bot: Duebel Viruleedung gefléckt → %s',
    'lt': u'robotas: Taisomas dvigubas peradresavimas → %s',
    'mk': u'Бот: Исправка на двојни пренасочувања → %s',
    'nds':u'Bot: Dubbelte Wiederleiden rutmakt → %s',
    'nl': u'Bot: dubbele doorverwijzing gecorrigeerd aan %s',
    'nn': u'robot: retta dobbel omdirigering → %s',
    'no': u'bot: Retter dobbel omdirigering → %s',
    'pl': u'Robot naprawia podwójne przekierowanie → %s',
    'pt': u'Bot: Corrigido duplo redirecionamento → %s',
    'ru': u'Робот: исправление двойного перенаправления → %s',
    'sr': u'Бот: Поправка дуплих преусмерења → %s',
    'sv': u'Robot: Rättar dubbel omdirigering → %s',
    'szl':u'Robot sprowjo tuplowane przekerowańa → %s',
    'th': u'โรบอต: แก้หน้าเปลี่ยนทางซ้ำซ้อน → %s',
    'tr': u'Bot değişikliği: Yönlendirmeye olan yönlendirme → %s',
    'uk': u'Робот: виправлення подвійного перенаправлення → %s',
    'war':u'Robot: Gin-ayad in nagduduha nga redirek → %s',
    'yi': u'באט: פארראכטן פארטאפלטע ווייטערפירונג → %s',
    'zh': u'機器人:修正雙重重定向 → %s',
    'zh-yue': u'機械人：拉直連串跳轉 → %s',
    'zh-classical': u'僕:復修渡口 → %s',
}

# Reason for deleting broken redirects
reason_broken={
    'ar': u'روبوت: هدف التحويلة غير موجود',
    'be-x-old': u'Робат: мэта перанакіраваньня не існуе',
    'cs': u'Přerušené přesměrování',
    'de': u'Bot: Weiterleitungsziel existiert nicht',
    'en': u'[[WP:CSD#G8|G8]]: [[Wikipedia:Redirect|Redirect]] to a deleted or non-existent page',
    'es': u'Robot: La página a la que redirige no existe',
    'fa': u'ربات:تغییرمسیر مقصد ندارد',
    'fi': u'Botti: Ohjauksen kohdesivua ei ole olemassa',
    'fr': u'Robot : Cible du redirect inexistante',
    'ga': u'Róbó : Targaid athsheoladh ar iarraidh',
    'he': u'בוט: יעד ההפניה אינו קיים',
    'it': u'Bot: Il redirect indirizza ad una pagina inesistente',
    'ja': u'ロボットによる:リダイレクトの目標は存在しませんでした',
    'ka': u'რობოტი: გადამისამართებული გვერდი არ არსებობს',
    'ko': u'로봇: 끊긴 넘겨주기',
    'kk': u'Бот: Айдату нысанасы жоқ болды',
    'ksh':u'Bot: Dė [[Special:BrokenRedirects|Ömlëijdong jingk ennet Liiere]]',
    'lt': u'robotas: Peradresavimas į niekur',
    'nds':u'Bot: Kaputte Wiederleiden rutmakt',
    'nl': u'Bot: doelpagina doorverwijzing bestaat niet',
    'nn': u'robot: målet for omdirigeringa eksisterer ikkje',
    'no': u'robot: målet for omdirigeringen eksisterer ikke',
    'pl': u'Robot: cel przekierowania nie istnieje',
    'pt': u'Bot: Redirecionamento não existe',
    'ru': u'Робот: перенаправление в никуда',
    'sr': u'Бот: Преусмерење не постоји',
    'th': u'โรบอต: หน้าเปลี่ยนทางเสีย',
    'tr': u'Bot değişikliği: Var olmayan sayfaya olan yönlendirme',
    'war':u'Robot: Waray dida an karadto-an han redirek',
    'yi': u'באט: ווײַטערפֿירן ציל עקזיסטירט נישט',
    'zh': u'機器人:該重定向的目標不存在',
    'zh-yue': u'機械人：跳轉目標唔存在',
}

# Summary message for putting broken redirect to speedy delete
sd_tagging_sum = {
    'ar': u'روبوت: وسم للحذف السريع',
    'cs': u'Robot označil ke smazání',
    'en': u'Robot: Tagging for speedy deletion',
    'ga': u'Róbó: Ag maircáil le luas-scrios',
    'it': u'Bot: +Da cancellare subito',
    'ja': u'ロボットによる:迷子のリダイレクトを即時削除へ',
    'ksh':u'Bot: Di Ömlëijdong jeiht noh nörjendwoh.',
    'nds':u'Bot: Kaputte Wiederleiden ward nich brukt',
    'nl': u'Bot: gemarkeerd voor snelle verwijdering',
    'war':u'Robot: Nautod o nagbinalikbalik nga redirek',
    'zh': u'機器人: 將損壞的重定向提報快速刪除',
}

# Insert deletion template into page with a broken redirect
sd_template = {
    'ar': u'{{شطب|تحويلة مكسورة}}',
    'cs': u'{{smazat|přerušené přesměrování}}',
    'en': u'{{db-r1}}',
    'ga': u'{{scrios|Athsheoladh briste}}',
    'it': u'{{Cancella subito|9}}',
    'ja': u'{{即時削除|壊れたリダイレクト}}',
    'ksh':u'{{Schmieß fott}}Di Ömlëijdong jeiht noh nörjendwoh hen.<br />--~~~~~\n\n',
    'nds':u'{{delete}}Kaputte Wiederleiden, wat nich brukt ward.<br />--~~~~\n\n',
    'war':u'{{delete}}Nautod o nagbinalikbalik nga redirek.--~~~~\n\n',
    'zh': u'{{delete|R1}}',
}

class RedirectGenerator:
    def __init__(self, xmlFilename=None, namespaces=[], offset=-1,
                 use_move_log=False, use_api=False, start=None, until=None,
                 number=None):
        self.site = wikipedia.getSite()
        self.xmlFilename = xmlFilename
        self.namespaces = namespaces
        self.offset = offset
        self.use_move_log = use_move_log
        self.use_api = use_api
        self.api_start = start
        self.api_until = until
        self.api_number = number

    def get_redirects_from_dump(self, alsoGetPageTitles=False):
        '''
        Load a local XML dump file, look at all pages which have the
        redirect flag set, and find out where they're pointing at. Return
        a dictionary where the redirect names are the keys and the redirect
        targets are the values.
        '''
        xmlFilename = self.xmlFilename
        redict = {}
        # open xml dump and read page titles out of it
        dump = xmlreader.XmlDump(xmlFilename)
        redirR = self.site.redirectRegex()
        readPagesCount = 0
        if alsoGetPageTitles:
            pageTitles = set()
        for entry in dump.parse():
            readPagesCount += 1
            # always print status message after 10000 pages
            if readPagesCount % 10000 == 0:
                wikipedia.output(u'%i pages read...' % readPagesCount)
            if len(self.namespaces) > 0:
                if wikipedia.Page(self.site, entry.title).namespace() \
                        not in self.namespaces:
                    continue
            if alsoGetPageTitles:
                pageTitles.add(entry.title.replace(' ', '_'))

            m = redirR.match(entry.text)
            if m:
                target = m.group(1)
                # There might be redirects to another wiki. Ignore these.
                for code in self.site.family.langs.keys():
                    if target.startswith('%s:' % code) \
                            or target.startswith(':%s:' % code):
                        if code == self.site.language():
                        # link to our wiki, but with the lang prefix
                            target = target[(len(code)+1):]
                            if target.startswith(':'):
                                target = target[1:]
                        else:
                            wikipedia.output(
                                u'NOTE: Ignoring %s which is a redirect to %s:'
                                % (entry.title, code))
                            target = None
                            break
                # if the redirect does not link to another wiki
                if target:
                    source = entry.title.replace(' ', '_')
                    target = target.replace(' ', '_')
                    # remove leading and trailing whitespace
                    target = target.strip('_')
                    # capitalize the first letter
                    if not wikipedia.getSite().nocapitalize:
                        source = source[:1].upper() + source[1:]
                        target = target[:1].upper() + target[1:]
                    if '#' in target:
                        target = target[:target.index('#')].rstrip("_")
                    if '|' in target:
                        wikipedia.output(
                            u'HINT: %s is a redirect with a pipelink.'
                            % entry.title)
                        target = target[:target.index('|')].rstrip("_")
                    if target: # in case preceding steps left nothing
                        redict[source] = target
        if alsoGetPageTitles:
            return redict, pageTitles
        else:
            return redict

    def get_redirect_pageids_via_api(self, number=u'max', namespaces=[],
                                     start=None, until=None):
        """
        Generator which will yield page IDs of Pages that are redirects.
        Get number of page ids in one go.
        Iterates over namespaces, Main if an empty list.
        In each namespace, start alphabetically from a pagetitle start,
        which need not exist.
        """
        if namespaces == []:
            namespaces = [ 0 ]
        params = {
            'action':'query',
            'list':'allpages',
            'apfilterredir':'redirects',
            'aplimit':number,
            'apdir':'ascending',
            #'':'',
        }
        for ns in namespaces:
            # print (ns)
            params['apnamespace'] = ns
            # print (apiQns)
            while True:
                if start:
                    params['apfrom'] = start
                data = query.GetData(params, self.site)
                if "limits" in data: # process aplimit = max
                    params['aplimit'] = int(data['limits']['allpages'])
                # wikipedia.output(u'===RESULT===\n%s\n' % data)
                for x in data['query']['allpages']:
                    if until and x['title'] == until:
                        break
                    yield x['pageid']

                if 'query-continue' in data:
                    params['apfrom'] = data['query-continue']['allpages']['apfrom']
                else:
                    break

    def _next_redirects_via_api_commandline(self, number='max', namespaces=[],
                                            start=None, until=None ):
        """
        Return a generator that retrieves pageids from the API 500 at a time
        and yields them as a list
        """
        if namespaces == []:
            namespaces = [ 0 ]
        apiQ = []
        for pageid in self.get_redirect_pageids_via_api(number, namespaces,
                                                        start, until):
            apiQ.append(pageid)
            if len(apiQ) >= 500:
                yield apiQ
                apiQ = []
        if apiQ:
            yield apiQ

    def get_redirects_via_api(self, number=u'max', namespaces=[], start=None,
                              until=None, maxlen=8):
        """
        Return a generator that yields tuples of data about redirect Pages:
            0 - page title of a redirect page
            1 - type of redirect:
                         0 - broken redirect, target page title missing
                         1 - normal redirect, target page exists and is not a
                             redirect
                 2..maxlen - start of a redirect chain of that many redirects
                             (currently, the API seems not to return sufficient
                             data to make these return values possible, but
                             that may change)
                  maxlen+1 - start of an even longer chain, or a loop
                             (currently, the API seems not to return sufficient
                             data to allow this return values, but that may
                             change)
                      None - start of a redirect chain of unknown length, or loop
            2 - target page title of the redirect, or chain (may not exist)
            3 - target page of the redirect, or end of chain, or page title where
                chain or loop detecton was halted, or None if unknown
        Get number of page ids in one go.
        Iterates over namespaces, Main if an empty list.
        In each namespace, start alphabetically from a pagetitle start, which
        need not exist.
        """
        import urllib
        if namespaces == []:
            namespaces = [ 0 ]
        params = {
            'action':'query',
            'redirects':1,
            #'':'',
        }
        for apiQ in self._next_redirects_via_api_commandline(
                                number, namespaces, start, until):
            params['pageids'] = apiQ
            data = query.GetData(params, self.site)
            redirects = {}
            pages = {}
            redirects = dict((x['from'], x['to'])
                             for x in data['query']['redirects'])

            for pagetitle in data['query']['pages'].values():
                if 'missing' in pagetitle and 'pageid' not in pagetitle:
                    pages[pagetitle['title']] = False
                else:
                    pages[pagetitle['title']] = True
            for redirect in redirects:
                target = redirects[redirect]
                result = 0
                final = None
                try:
                    if pages[target]:
                        final = target
                        try:
                            while result <= maxlen:
                               result += 1
                               final = redirects[final]
                            # result = None
                        except KeyError:
                            pass
                except KeyError:
                    result = None
                    pass
                yield (redirect, result, target, final)

    def retrieve_broken_redirects(self):
        if self.use_api:
            count = 0
            for (pagetitle, type, target, final) \
                    in self.get_redirects_via_api(
                        namespaces=self.namespaces,
                        start=self.api_start,
                        until=self.api_until, maxlen=2):
                if type == 0:
                    yield pagetitle
                    if self.api_number:
                        count += 1
                        if count >= self.api_number:
                            break

        elif self.xmlFilename == None:
            # retrieve information from the live wiki's maintenance page
            # broken redirect maintenance page's URL
            path = self.site.broken_redirects_address(default_limit = False)
            wikipedia.output(u'Retrieving special page...')
            maintenance_txt = self.site.getUrl(path)

            # regular expression which finds redirects which point to a
            # non-existing page inside the HTML
            Rredir = re.compile('\<li\>\<a href=".+?" title="(.*?)"')

            redir_names = Rredir.findall(maintenance_txt)
            wikipedia.output(u'Retrieved %d redirects from special page.\n'
                             % len(redir_names))
            for redir_name in redir_names:
                yield redir_name
        else:
            # retrieve information from XML dump
            wikipedia.output(
                u'Getting a list of all redirects and of all page titles...')
            redirs, pageTitles = self.get_redirects_from_dump(
                                            alsoGetPageTitles=True)
            for (key, value) in redirs.iteritems():
                if value not in pageTitles:
                    yield key

    def retrieve_double_redirects(self):
        if self.use_api:
            count = 0
            for (pagetitle, type, target, final) \
                    in self.get_redirects_via_api(
                         namespaces=self.namespaces, start=self.api_start,
                         until=self.api_until, maxlen = 2):
                if type != 0 and type != 1:
                    yield pagetitle
                    if self.api_number:
                        count += 1
                        if count >= self.api_number:
                            break

        elif self.xmlFilename == None:
            if self.use_move_log:
                for redir_page in self.get_moved_pages_redirects():
                    yield redir_page.title()
                return
            # retrieve information from the live wiki's maintenance page
            # double redirect maintenance page's URL
#            wikipedia.config.special_page_limit = 1000
            path = self.site.double_redirects_address(default_limit = False)
            wikipedia.output(u'Retrieving special page...')
            maintenance_txt = self.site.getUrl(path)

            # regular expression which finds redirects which point to
            # another redirect inside the HTML
            Rredir = re.compile('\<li\>\<a href=".+?" title="(.*?)">')
            redir_names = Rredir.findall(maintenance_txt)
            wikipedia.output(u'Retrieved %i redirects from special page.\n'
                             % len(redir_names))
            for redir_name in redir_names:
                yield redir_name
        else:
            redict = self.get_redirects_from_dump()
            num = 0
            for (key, value) in redict.iteritems():
                num += 1
                # check if the value - that is, the redirect target - is a
                # redirect as well
                if num > self.offset and value in redict:
                    yield key
                    wikipedia.output(u'\nChecking redirect %i of %i...'
                                     % (num + 1, len(redict)))

    move_regex = re.compile(
            r'moved <a href.*?>(.*?)</a> to <a href=.*?>.*?</a>.*?</li>')

    def get_moved_pages_redirects(self):
        '''generate redirects to recently-moved pages'''
        # this will run forever, until user interrupts it
        import datetime

        if self.offset <= 0:
            self.offset = 1
        offsetpattern = re.compile(
            r"""\(<a href="/w/index\.php\?title=Special:Log&amp;offset=(\d+)"""
            r"""&amp;limit=500&amp;type=move" title="Special:Log" rel="next">"""
            r"""older 500</a>\)""")
        start = datetime.datetime.utcnow() \
                 - datetime.timedelta(0, self.offset*3600)
        # self.offset hours ago
        offset_time = start.strftime("%Y%m%d%H%M%S")
        while True:
            move_url = \
                self.site.path() + "?title=Special:Log&limit=500&offset=%s&type=move"\
                       % offset_time
            try:
                move_list = self.site.getUrl(move_url)
                if wikipedia.verbose:
                    wikipedia.output(u"[%s]" % offset_time)
            except:
                import traceback
                wikipedia.output(unicode(traceback.format_exc()))
                return
            g = self.move_regex.findall(move_list)
            if wikipedia.verbose:
                wikipedia.output(u"%s moved pages" % len(g))
            for moved_title in g:
                moved_page = wikipedia.Page(self.site, moved_title)
                try:
                    if not moved_page.isRedirectPage():
                        continue
                except wikipedia.BadTitle:
                    continue
                except wikipedia.ServerError:
                    continue
                # moved_page is now a redirect, so any redirects pointing
                # to it need to be changed
                try:
                    for page in moved_page.getReferences(follow_redirects=True,
                                                         redirectsOnly=True):
                        yield page
                except wikipedia.NoPage:
                    # original title must have been deleted after move
                    continue
            m = offsetpattern.search(move_list)
            if not m:
                break
            offset_time = m.group(1)

class RedirectRobot:
    def __init__(self, action, generator, always=False, number=None):
        self.site = wikipedia.getSite()
        self.action = action
        self.generator = generator
        self.always = always
        self.number = number
        self.exiting = False

    def prompt(self, question):
        if not self.always:
            choice = wikipedia.inputChoice(question,
                                           ['Yes', 'No', 'All', 'Quit'],
                                           ['y', 'N', 'a', 'q'], 'N')
            if choice == 'n':
                return False
            elif choice == 'q':
                self.exiting = True
                return False
            elif choice == 'a':
                self.always = True
        return True

    def delete_broken_redirects(self):
        # get reason for deletion text
        reason = wikipedia.translate(self.site, reason_broken)
        for redir_name in self.generator.retrieve_broken_redirects():
            self.delete_1_broken_redirect( redir_name, reason)
            if self.exiting:
                break

    def delete_1_broken_redirect(self, redir_name, reason):
            redir_page = wikipedia.Page(self.site, redir_name)
            # Show the title of the page we're working on.
            # Highlight the title in purple.
            wikipedia.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<"
                              % redir_page.title())
            try:
                targetPage = redir_page.getRedirectTarget()
            except wikipedia.IsNotRedirectPage:
                wikipedia.output(u'%s is not a redirect.' % redir_page.title())
            except wikipedia.NoPage:
                wikipedia.output(u'%s doesn\'t exist.' % redir_page.title())
            else:
                try:
                    targetPage.get()
                except wikipedia.NoPage:
                    if self.prompt(
            u'Redirect target %s does not exist. Do you want to delete %s?'
                                   % (targetPage.aslink(),
                                      redir_page.aslink())):
                        try:
                            redir_page.delete(reason, prompt = False)
                        except wikipedia.NoUsername:
                            if targetPage.site().lang in sd_template \
                                    and targetPage.site().lang in sd_tagging_sum:
                                wikipedia.output(
            u"No sysop in user-config.py, put page to speedy deletion.")
                                content = redir_page.get(get_redirect=True)
                                content = wikipedia.translate(
                                    targetPage.site().lang,
                                    sd_template)+"\n"+content
                                summary = wikipedia.translate(
                                    targetPage.site().lang,
                                    sd_tagging_sum)
                                redir_page.put(content, summary)

                except wikipedia.IsRedirectPage:
                    wikipedia.output(
            u'Redirect target %s is also a redirect! Won\'t delete anything.'
                        % targetPage.aslink())
                else:
                    #we successfully get the target page, meaning that
                    #it exists and is not a redirect: no reason to touch it.
                    wikipedia.output(
            u'Redirect target %s does exist! Won\'t delete anything.'
                        % targetPage.aslink())
            wikipedia.output(u'')

    def fix_double_redirects(self):
        for redir_name in self.generator.retrieve_double_redirects():
            self.fix_1_double_redirect(redir_name)
            if self.exiting:
                break

    def fix_1_double_redirect(self,  redir_name):
            redir = wikipedia.Page(self.site, redir_name)
            # Show the title of the page we're working on.
            # Highlight the title in purple.
            wikipedia.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<"
                              % redir.title())
            newRedir = redir
            redirList = []  # bookkeeping to detect loops
            while True:
                redirList.append(u'%s:%s' % (newRedir.site().lang,
                                             newRedir.sectionFreeTitle()))
                try:
                    targetPage = newRedir.getRedirectTarget()
                except wikipedia.IsNotRedirectPage:
                    if len(redirList) == 1:
                        wikipedia.output(u'Skipping: Page %s is not a redirect.'
                                         % redir.aslink())
                        break  #do nothing
                    elif len(redirList) == 2:
                        wikipedia.output(
                            u'Skipping: Redirect target %s is not a redirect.'
                            % newRedir.aslink())
                        break  # do nothing
                except wikipedia.SectionError:
                    wikipedia.output(
                        u'Warning: Redirect target section %s doesn\'t exist.'
                          % newRedir.aslink())
                except wikipedia.BadTitle, e:
                    # str(e) is in the format 'BadTitle: [[Foo]]'
                    wikipedia.output(
                        u'Warning: Redirect target %s is not a valid page title.'
                          % str(e)[10:])
                #sometimes this error occures. Invalid Title starting with a '#'
                except wikipedia.InvalidTitle, err:
                    wikipedia.output(u'Warning: %s' % err)
                    break
                except wikipedia.NoPage:
                    if len(redirList) == 1:
                        wikipedia.output(u'Skipping: Page %s does not exist.'
                                            % redir.aslink())
                        break
                    else:
                        if self.always:
                            wikipedia.output(
                                u"Skipping: Redirect target %s doesn't exist."
                                % newRedir.aslink())
                            break  # skip if automatic
                        else:
                            wikipedia.output(
                                u"Warning: Redirect target %s doesn't exist."
                                % newRedir.aslink())
                except wikipedia.ServerError:
                    wikipedia.output(u'Skipping: Server Error')
                    break
                else:
                    wikipedia.output(
                        u'   Links to: %s.'
                          % targetPage.aslink())
                    if targetPage.site() != self.site:
                        wikipedia.output(
                u'Warning: redirect target (%s) is on a different site.'
                             % (targetPage.aslink()))
                        if self.always:
                            break  # skip if automatic
                    # watch out for redirect loops
                    if redirList.count(u'%s:%s'
                                       % (targetPage.site().lang,
                                          targetPage.sectionFreeTitle())
                                      ) > 0:
                        wikipedia.output(
                           u'Warning: Redirect target %s forms a redirect loop.'
                              % targetPage.aslink())
                        break ###xqt doesn't work. edits twice!
                        try:
                            content = targetPage.get(get_redirect=True)
                        except wikipedia.SectionError:
                            content = wikipedia.Page(
                                          targetPage.site(),
                                          targetPage.sectionFreeTitle()
                                      ).get(get_redirect=True)
                        if targetPage.site().lang in sd_template \
                                and targetPage.site().lang in sd_tagging_sum:
                            wikipedia.output(u"Tagging redirect for deletion")
                            # Delete the two redirects
                            content = wikipedia.translate(
                                        targetPage.site().lang,
                                        sd_template)+"\n"+content
                            summ = wikipedia.translate(targetPage.site().lang,
                                                       sd_tagging_sum)
                            targetPage.put(content, summ)
                            redir.put(content, summ)
                        else:
                            break # TODO Better implement loop redirect
                    else:
                        newRedir = targetPage
                        continue #
                try:
                    oldText = redir.get(get_redirect=True)
                except wikipedia.BadTitle:
                    wikipedia.output(u"Bad Title Error")
                    break
                text = self.site.redirectRegex().sub(
                        '#%s %s' %
                            (self.site.redirect( True ),
                             targetPage.aslink()),
                        oldText)
                if text == oldText:
                    break
                summary = wikipedia.translate(self.site, msg_double)\
                          % targetPage.aslink()
                wikipedia.showDiff(oldText, text)
                if self.prompt(u'Do you want to accept the changes?'):
                    try:
                        redir.put(text, summary)
                    except wikipedia.LockedPage:
                        wikipedia.output(u'%s is locked.' % redir.title())
                    except wikipedia.SpamfilterError, error:
                        wikipedia.output(
                            u"Saving page [[%s]] prevented by spam filter: %s"
                             % (redir.title(), error.url))
                    except wikipedia.PageNotSaved, error:
                        wikipedia.output(u"Saving page [[%s]] failed: %s"
                             % (redir.title(), error))
                    except wikipedia.NoUsername:
                        wikipedia.output(
                            u"Page [[%s]] not saved; sysop privileges required."
                             % redir.title())
                    except wikipedia.Error, error:
                        wikipedia.output(
                        u"Unexpected error occurred trying to save [[%s]]: %s"
                             % (redir.title(), error))
                break

    def fix_double_or_delete_broken_redirects(self):
        # TODO: part of this should be moved to generator, the rest merged into self.run()
        # get reason for deletion text
        delete_reason = wikipedia.translate(self.site, reason_broken)
        count = 0
        for (redir_name, code, target, final)\
                in self.generator.get_redirects_via_api(
                     namespaces=self.generator.namespaces,
                     start=self.generator.api_start,
                     until=self.generator.api_until,
                     maxlen = 2):
            if code == 1:
                continue
            elif code == 0:
                self.delete_1_broken_redirect(redir_name, delete_reason)
                count += 1
            else:
                self.fix_1_double_redirect(redir_name)
                count += 1
            # print ('%s .. %s' % (count, self.number))
            if self.exiting or ( self.number and count >= self.number ):
                break

    def run(self):
        # TODO: make all generators return a redicet type indicator,
        #        thus make them usabile with 'both'
        if self.action == 'double':
            self.fix_double_redirects()
        elif self.action == 'broken':
            self.delete_broken_redirects()
        elif self.action == 'both':
            self.fix_double_or_delete_broken_redirects()

def main(*args):
    # read command line parameters
    # what the bot should do (either resolve double redirs, or delete broken
    # redirs)
    action = None
    # where the bot should get his infos from (either None to load the
    # maintenance special page from the live wiki, or the filename of a
    # local XML dump file)
    xmlFilename = None
    # Which namespace should be processed when using a XML dump
    # default to -1 which means all namespaces will be processed
    namespaces = []
    # at which redirect shall we start searching double redirects again
    # (only with dump); default to -1 which means all redirects are checked
    offset = -1
    moved_pages = False
    api = False
    start = ''
    until = ''
    number = None
    always = False
    for arg in wikipedia.handleArgs(*args):
        if arg == 'double' or arg == 'do':
            action = 'double'
        elif arg == 'broken' or arg == 'br':
            action = 'broken'
        elif arg == 'both':
            action = 'both'
        elif arg == '-api':
            api = True
        elif arg.startswith('-xml'):
            if len(arg) == 4:
                xmlFilename = wikipedia.input(
                                u'Please enter the XML dump\'s filename: ')
            else:
                xmlFilename = arg[5:]
        elif arg.startswith('-moves'):
            moved_pages = True
        elif arg.startswith('-namespace:'):
            ns = arg[11:]
            if ns == '':
        ## "-namespace:" does NOT yield -namespace:0 further down the road!
                ns = wikipedia.input(
                        u'Please enter a namespace by its number: ')
#                       u'Please enter a namespace by its name or number: ')
#  TODO! at least for some generators.
            if ns == '':
               ns = '0'
            try:
                ns = int(ns)
            except ValueError:
#-namespace:all Process all namespaces. Works only with the API read interface.
               pass
            if not ns in namespaces:
               namespaces.append(ns)
        elif arg.startswith('-offset:'):
            offset = int(arg[8:])
        elif arg.startswith('-start:'):
            start = arg[7:]
        elif arg.startswith('-until:'):
            until = arg[7:]
        elif arg.startswith('-number:'):
            number = int(arg[8:])
        elif arg == '-always':
            always = True
        else:
            wikipedia.output(u'Unknown argument: %s' % arg)

    if not action or (api and moved_pages) or (xmlFilename and moved_pages)\
                  or (api and xmlFilename):
        wikipedia.showHelp('redirect')
    else:
        gen = RedirectGenerator(xmlFilename, namespaces, offset, moved_pages,
                                api, start, until, number)
        bot = RedirectRobot(action, gen, always, number)
        bot.run()

if __name__ == '__main__':
    try:
        main()
    finally:
        wikipedia.stopme()
