#!/usr/bin/python
# -*- coding: utf-8  -*-

"""
This script goes over multiple pages, searches for pages where <references />
is missing although a <ref> tag is present, and in that case adds a new
references section.

These command line parameters can be used to specify which pages to work on:

&params;

    -xml          Retrieve information from a local XML dump (pages-articles
                  or pages-meta-current, see http://download.wikimedia.org).
                  Argument can also be given as "-xml:filename".

    -namespace:n  Number or name of namespace to process. The parameter can be
                  used multiple times. It works in combination with all other
                  parameters, except for the -start parameter. If you e.g.
                  want to iterate over all categories starting at M, use
                  -start:Category:M.

    -always       Don't prompt you for each replacement.

All other parameters will be regarded as part of the title of a single page,
and the bot will only work on that single page.

It is strongly recommended not to run this script over the entire article
namespace (using the -start) parameter, as that would consume too much
bandwidth. Instead, use the -xml parameter, or use another way to generate
a list of affected articles
"""

__version__='$Id$'

import wikipedia, pagegenerators, catlib
import editarticle
import re, sys

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;':     pagegenerators.parameterHelp,
}

# Summary messages in different languages
msg = {
    'ar':u'روبوت: إضافة وسم <references /> مفقود',
    'cs':u'Robot doplnil chybějící <references />',
    'de':u'Bot: Trage fehlendes <references /> nach',
    'en':u'Robot: Adding missing <references /> tag',
    'eo':u'Roboto: Aldono de "<references />"',
    'fa':u'ربات:تگ رفرنسز فراموش شده‌است',
    'fi':u'Botti lisäsi puuttuvan {{viitteet}}-mallineen',
    'he':u'בוט: מוסיף תגית <references /> חסרה',
    'hu':u'Hiányzó {{Források}} pótlása',
    'it':u'Bot: Aggiungo il tag <references /> mancante',
    'ja':u'ロボットによる: <references /> タグの補完。',
    'ko':u'봇: 이전에 없던 <references /> 추가',
    'lt':u'robotas: Pridedama trūkstama <references /> žymė',
    'nl':u'Bot: toevoeging ontbrekende <references /> tag',
    'pl':u'Robot dodaje szablon {{przypisy}}',
    'pt':u'Bot: Adicionando a tag <references />',
    'zh':u'機器人: 增加遺失的 <references /> 標籤',
    'fr':u'Robot: Ajout de la balise <references /> manquante',
}

# References sections are usually placed before further reading / external
# link sections. This dictionary defines these sections, sorted by priority.
# For example, on an English wiki, the script would place the "References"
# section in front of the "Further reading" section, if that existed.
# Otherwise, it would try to put it in front of the "External links" section,
# or if that fails, the "See also" section, etc.
placeBeforeSections = {
    'ar': [              # no explicit policy on where to put the references
        u'وصلات خارجية',
        u'انظر أيضا',
        u'ملاحظات'
    ],
    'cs': [
        u'Reference',
        u'Poznámky',
    ],
    'de': [              # no explicit policy on where to put the references
        u'Literatur',
        u'Weblinks',
        u'Siehe auch',
        u'Weblink',      # bad, but common singular form of Weblinks
    ],
    'en': [              # no explicit policy on where to put the references
        u'Further reading',
        u'External links',
        u'See also',
        u'Notes'
    ],
    'eo': [
        u'Eksteraj ligiloj',
        u'Ekstera ligilo',
        u'Eksteraj ligoj',
        u'Ekstera ligo',
        u'Rete'
    ],
    'es': [
        u'Enlaces externos',
        u'Véase también',
        u'Notas',
    ],
    'fa': [
        u'پیوند به بیرون',
        u'پانویس',
        u'جستارهای وابسته'
    ],
    'fi': [
        u'Kirjallisuutta',
        u'Aiheesta muualla',
        u'Ulkoiset linkit',
        u'Linkkejä',
    ],
    'fr': [
        u'Liens externes',
        u'Voir aussi',
        u'Notes'
    ],
    'hu': [
        u'Külső hivatkozások',
        u'Lásd még',
    ],
    'it': [
        u'Bibliografia',
        u'Voci correlate',
        u'Altri progetti',
        u'Collegamenti esterni',
        u'Vedi anche',
    ],
    'ja':[
        u'関連項目',
        u'参考文献',
        u'外部リンク',
    ],
    'ko':[               # no explicit policy on where to put the references
        u'외부 링크',
        u'외부링크',
        u'바깥 고리',
        u'바깥고리',
        u'바깥 링크',
        u'바깥링크'
        u'외부 고리',
        u'외부고리'
    ],
    'lt': [              # no explicit policy on where to put the references
        u'Nuorodos'
    ],
    'nl': [              # no explicit policy on where to put the references
        u'Literatuur',
        u'Zie ook',
        u'Externe verwijzingen',
        u'Externe verwijzing',
    ],
    'pl': [
        u'Źródła',
        u'Bibliografia',
        u'Zobacz też',
        u'Linki zewnętrzne',
    ],
    'pt': [
        u'Ligações externas',
        u'Veja também',
        u'Ver também',
        u'Notas',
    ],
    'sk': [
        u'Pozri aj',
    ],
    'zh': [
        u'外部連结',
        u'外部链接',
    ],
}

# Titles of sections where a reference tag would fit into.
# The first title should be the preferred one: It's the one that
# will be used when a new section has to be created.
referencesSections = {
    'ar': [             # not sure about which ones are preferred.
        u'مراجع',
        u'ملاحظات',
    ],
    'de': [             #see [[de:WP:REF]]
        u'Einzelnachweise',
        u'Fußnoten',
        u'Anmerkungen',
        u'Belege',
        u'Quellen',
        u'Quellenangaben',
    ],
    'en': [             # not sure about which ones are preferred.
        u'References',
        u'Footnotes',
        u'Notes',
    ],
    'eo': [
        u'Referencoj',
    ],
    'es': [
        u'Referencias',
        u'Notas',
    ],
    'fa': [
        u'منابع',
        u'منبع'
    ],
    'fi': [
        u'Lähteet',
        u'Viitteet',
    ],
    'fr': [             # [[fr:Aide:Note]]
        u'Notes et références',
        u'Références',
        u'References',
        u'Notes'
    ],
    'he': [
        u'הערות שוליים',
    ],
    'hu': [
        u'Források és jegyzetek',
        u'Források',
        u'Jegyzetek',
        u'Hivatkozások',
        u'Megjegyzések',
    ],
    'it': [
        u'Note',
        u'Riferimenti',
    ],
    'ja': [
        u'脚注',
        u'脚注欄',
        u'脚注・出典',
        u'出典',
        u'注釈',
        u'註',
    ],
    'ko': [
        u'주석',
        u'각주'
        u'주석 및 참고 자료'
        u'주석 및 참고자료',
        u'주석 및 참고 출처'
    ],
    'lt': [             # not sure about which ones are preferred.
        u'Šaltiniai',
        u'Literatūra',
    ],
    'nl': [             # not sure about which ones are preferred.
        u'Voetnoten',
        u'Voetnoot',
        u'Referenties',
        u'Noten',
        u'Bronvermelding',
    ],
    'pl': [
        u'Przypisy',
        u'Ogólne przypisy',
        u'Notatki',
    ],
    'pt': [
        u'Referências',
    ],
    'sk': [
        u'Referencie',
    ],
    'zh': [
        u'參考文獻',
        u'参考文献',
        u'參考資料',
        u'参考资料',
        u'資料來源',
        u'资料来源',
        u'參見',
        u'参见',
        u'參閱',
        u'参阅',
    ],
}

# Templates which include a <references /> tag. If there is no such template
# on your wiki, you don't have to enter anything here.
referencesTemplates = {
    'wikipedia': {
        'ar': [u'Reflist',u'ثبت المراجع',u'قائمة المراجع'],
        'en': [u'Reflist',u'Refs',u'FootnotesSmall',u'Reference',
               u'Ref-list',u'Reference list',u'References-small',u'Reflink',
               u'Footnotes',u'FootnotesSmall'],
        'eo': [u'Referencoj'],
        'es': ['Listaref', 'Reflist', 'muchasref'],
        'fa': [u'Reflist',u'Refs',u'FootnotesSmall',u'Reference',u'پانویس',u'Reflist',u'پانویس‌ها ',u'پانویس ۲',u'پانویس۲'],
        'fi': [u'Viitteet', u'Reflist'],
        'fr': [u'Références',u'Notes', u'References', u'Reflist'],
        'hu': [u'reflist',u'források'],
        'it': [u'References'],
        'ja': [u'Reflist', u'脚注リスト'],
        'ko': [u'주석', u'Reflist'],
        'lt': [u'Reflist', u'Ref', u'Litref'],
        'nl': [u'Reflist',u'Refs',u'FootnotesSmall',u'Reference',
               u'Ref-list',u'Reference list',u'References-small',u'Reflink',
               u'Referenties',u'Bron',u'Bronnen/noten/referenties',u'Bron2',
               u'Bron3',u'ref',u'references',u'appendix',
               u'Noot',u'FootnotesSmall'],
        'pl': [u'przypisy', u'Przypisy'],
        'pt': [u'Notas', 'ref-section'],
        'zh': [u'Reflist'],
    },
}

# Text to be added instead of the <references /> tag.
# Define this only if required by your wiki.
referencesSubstitute = {
    'wikipedia': {
        'fi': u'{{viitteet}}',
        'hu': u'{{Források}}',
    },
}

class XmlDumpNoReferencesPageGenerator:
    """
    Generator which will yield Pages that might lack a references tag.
    These pages will be retrieved from a local XML dump file
    (pages-articles or pages-meta-current).
    """
    def __init__(self, xmlFilename):
        """
        Arguments:
            * xmlFilename  - The dump's path, either absolute or relative
        """
        self.xmlFilename = xmlFilename
        self.refR = re.compile('</ref>', re.IGNORECASE)
        # The references tab can contain additional spaces and a group attribute.
        self.referencesR = re.compile('<references.*?/>', re.IGNORECASE)

    def __iter__(self):
        import xmlreader
        dump = xmlreader.XmlDump(self.xmlFilename)
        for entry in dump.parse():
            text = wikipedia.removeDisabledParts(entry.text)
            if self.refR.search(text) and not self.referencesR.search(text):
                yield wikipedia.Page(wikipedia.getSite(), entry.title)

class NoReferencesBot:

    def __init__(self, generator, always = False):
        self.generator = generator
        self.always = always
        self.site = wikipedia.getSite()
        self.refR = re.compile('</ref>', re.IGNORECASE)
        self.referencesR = re.compile('<references.*?/>', re.IGNORECASE)
        try:
            self.referencesTemplates = referencesTemplates[wikipedia.getSite().family.name][wikipedia.getSite().lang]
        except KeyError:
            self.referencesTemplates = []
        try:
            self.referencesText = referencesSubstitute[wikipedia.getSite().family.name][wikipedia.getSite().lang]
        except KeyError:
            self.referencesText = u'<references />'

    def lacksReferences(self, text, verbose = True):
        """
        Checks whether or not the page is lacking a references tag.
        """
        oldTextCleaned = wikipedia.removeDisabledParts(text)
        if self.referencesR.search(oldTextCleaned):
            if verbose:
                wikipedia.output(u'No changes necessary: references tag found.')
            return False
        elif self.referencesTemplates:
            templateR = u'{{(' + u'|'.join(self.referencesTemplates) + ')'
            if re.search(templateR, oldTextCleaned, re.IGNORECASE):
                if verbose:
                    wikipedia.output(u'No changes necessary: references template found.')
                return False
        elif not self.refR.search(oldTextCleaned):
            if verbose:
                wikipedia.output(u'No changes necessary: no ref tags found.')
            return False
        else:
            if verbose:
                wikipedia.output(u'Found ref without references.')
            return True

    def addReferences(self, oldText):
        """
        Tries to add a references tag into an existing section where it fits
        into. If there is no such section, creates a new section containing
        the references tag.
        * Returns : The modified pagetext
        """

        # Is there an existing section where we can add the references tag?
        for section in wikipedia.translate(self.site, referencesSections):
            sectionR = re.compile(r'\r\n=+ *%s *=+ *\r\n' % section)
            index = 0
            while index < len(oldText):
                match = sectionR.search(oldText, index)
                if match:
                    if wikipedia.isDisabled(oldText, match.start()):
                        wikipedia.output('Existing  %s section is commented out, skipping.' % section)
                        index = match.end()
                    else:
                        wikipedia.output(u'Adding references tag to existing %s section...\n' % section)
                        newText = oldText[:match.end()] + u'\n' + self.referencesText + u'\n' + oldText[match.end():]
                        return newText
                else:
                    break

        # Create a new section for the references tag
        for section in wikipedia.translate(self.site, placeBeforeSections):
            # Find out where to place the new section
            sectionR = re.compile(r'\r\n(?P<ident>=+) *%s *(?P=ident) *\r\n' % section)
            index = 0
            while index < len(oldText):
                match = sectionR.search(oldText, index)
                if match:
                    if wikipedia.isDisabled(oldText, match.start()):
                        wikipedia.output('Existing  %s section is commented out, won\'t add the references in front of it.' % section)
                        index = match.end()
                    else:
                        wikipedia.output(u'Adding references section before %s section...\n' % section)
                        index = match.start()
                        ident = match.group('ident')
                        return self.createReferenceSection(oldText, index, ident)
                else:
                    break
        # This gets complicated: we want to place the new references
        # section over the interwiki links and categories, but also
        # over all navigation bars, persondata, and other templates
        # that are at the bottom of the page. So we need some advanced
        # regex magic.
        # The strategy is: create a temporary copy of the text. From that,
        # keep removing interwiki links, templates etc. from the bottom.
        # At the end, look at the length of the temp text. That's the position
        # where we'll insert the references section.
        catNamespaces = '|'.join(self.site.category_namespaces())
        categoryPattern  = r'\[\[\s*(%s)\s*:[^\n]*\]\]\s*' % catNamespaces
        interwikiPattern = r'\[\[([a-zA-Z\-]+)\s?:([^\[\]\n]*)\]\]\s*'
        # won't work with nested templates
        templatePattern  = r'{{((?!}}).)+?}}\s*' # the negative lookahead assures that we'll match the last template occurence in the temp text.
        commentPattern   = r'<!--((?!-->).)*?-->\s*'
        metadataR = re.compile(r'(\r\n)?(%s|%s|%s|%s)$' % (categoryPattern, interwikiPattern, templatePattern, commentPattern), re.DOTALL)
        tmpText = oldText
        while True:
            match = metadataR.search(tmpText)
            if match:
                tmpText = tmpText[:match.start()]
            else:
                break
        wikipedia.output(u'Found no section that can be preceeded by a new references section. Placing it before interwiki links, categories, and bottom templates.')
        index = len(tmpText)
        return self.createReferenceSection(oldText, index)

    def createReferenceSection(self, oldText, index, ident = '=='):
        newSection = u'\n%s %s %s\n%s\n' % (ident, wikipedia.translate(self.site, referencesSections)[0], ident, self.referencesText)
        return oldText[:index] + newSection + oldText[index:]

    def save(self, page, newText):
        """
        Saves the page to the wiki, if the user accepts the changes made.
        """
        wikipedia.showDiff(page.get(), newText)
        if not self.always:
            choice = wikipedia.inputChoice(u'Do you want to accept these changes?', ['Yes', 'No', 'Always yes'], ['y', 'N', 'a'], 'Y')
            if choice == 'n':
                return
            elif choice == 'a':
                self.always = True

        if self.always:
            try:
                page.put(newText)
            except wikipedia.EditConflict:
                wikipedia.output(u'Skipping %s because of edit conflict' % (page.title(),))
            except wikipedia.SpamfilterError, e:
                wikipedia.output(u'Cannot change %s because of blacklist entry %s' % (page.title(), e.url))
            except wikipedia.LockedPage:
                wikipedia.output(u'Skipping %s (locked page)' % (page.title(),))
        else:
            # Save the page in the background. No need to catch exceptions.
            page.put_async(newText)
        return

    def run(self):
        comment = wikipedia.translate(self.site, msg)
        wikipedia.setAction(comment)

        for page in self.generator:
            # Show the title of the page we're working on.
            # Highlight the title in purple.
            wikipedia.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<" % page.title())
            try:
                text = page.get()
            except wikipedia.NoPage:
                wikipedia.output(u"Page %s does not exist?!" % page.aslink())
                continue
            except wikipedia.IsRedirectPage:
                wikipedia.output(u"Page %s is a redirect; skipping." % page.aslink())
                continue
            except wikipedia.LockedPage:
                wikipedia.output(u"Page %s is locked?!" % page.aslink())
                continue
            if self.lacksReferences(text):
                newText = self.addReferences(text)
                self.save(page, newText)

def main():
    #page generator
    gen = None
    # This temporary array is used to read the page title if one single
    # page to work on is specified by the arguments.
    pageTitle = []
    # Which namespaces should be processed?
    # default to [] which means all namespaces will be processed
    namespaces = []
    # Never ask before changing a page
    always = False
    # This factory is responsible for processing command line arguments
    # that are also used by other scripts and that determine on which pages
    # to work on.
    genFactory = pagegenerators.GeneratorFactory()

    for arg in wikipedia.handleArgs():
        if arg.startswith('-xml'):
            if len(arg) == 4:
                xmlFilename = wikipedia.input(u'Please enter the XML dump\'s filename:')
            else:
                xmlFilename = arg[5:]
            gen = XmlDumpNoReferencesPageGenerator(xmlFilename)
        elif arg.startswith('-namespace:'):
            try:
                namespaces.append(int(arg[11:]))
            except ValueError:
                namespaces.append(arg[11:])
        elif arg == '-always':
            always = True
        else:
            if not genFactory.handleArg(arg):
                pageTitle.append(arg)

    if pageTitle:
        page = wikipedia.Page(wikipedia.getSite(), ' '.join(pageTitle))
        gen = iter([page])
    if not gen:
        gen = genFactory.getCombinedGenerator()
    if not gen:
        wikipedia.showHelp('noreferences')
    else:
        if namespaces != []:
            gen =  pagegenerators.NamespaceFilterPageGenerator(gen, namespaces)
        preloadingGen = pagegenerators.PreloadingGenerator(gen)
        bot = NoReferencesBot(preloadingGen, always)
        bot.run()

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()

