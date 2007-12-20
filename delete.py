# -*- coding: utf-8 -*-
"""
This script can be used to delete and undelete pages en masse.
Of course, you will need an admin account on the relevant wiki.

Syntax: python delete.py [-category categoryName]

Command line options:

-page:       Delete specified page
-cat:        Delete all pages in the given category.
-nosubcats:  Don't delete pages in the subcategories.
-links:      Delete all pages linked from a given page.
-file:       Delete all pages listed in a text file.
-ref:        Delete all pages referring from a given page.
-images:     Delete all images used on a given page.
-always:     Don't prompt to delete pages, just do it.
-summary:    Supply a custom edit summary.
-undelete:   Actually undelete pages instead of deleting.
             Obviously makes sense only with -page and -file.

Examples:

Delete everything in the category "To delete" without prompting.

    python delete.py -cat:"To delete" -always
"""
__version__ = '$Id$'
#
# Distributed under the terms of the MIT license.
#
import wikipedia, config, catlib
import pagegenerators

# Summary messages for deleting from a category.
msg_simple_delete = {
    'en': u'Bot: Deleting a list of files.',
    'he': u'בוט: מוחק רשימת דפים מתוך קובץ.',
    'nl': u'Bot: verwijdert een lijst met pagina\'s.',
    'pl': u'Robot usuwa pliki z listy.',
    'pt': u'Bot: Apagando um lista de arquivos.',
}
msg_delete_category = {
    'de': u'Bot: Lösche alle Seiten in Kategorie %s',
    'en': u'Robot - Deleting all pages from category %s',
    'he': u'בוט: מוחק את כל הדפים מהקטגוריה %s.',
    'fr': u'Bot: Supprime toutes pages de la catégorie %s',
    'lt': u'robotas: Trinami visi puslapiai iš kategorijos %s',
    'nl': u'Bot: verwijdert alle pagina\'s uit categorie %s',
    'pl': u'Robot usuwa wszystkie artykuły z kategorii %s',
    'pt': u'Bot: Apagando todas as páginas da categoria %s',
}
msg_delete_links = {
    'de': u'Bot: Lösche alle Seiten in %s verlinkten Seiten',
    'en': u'Robot - Deleting all pages linked from %s',
    'fr': u'Bot: Supprime toutes pages liées depuis %s',
    'he': u'בוט: מוחק את כל הדפים המקושרים מהדף %s.',
    'lt': u'robotas: Trinami visi puslapiai į kuriuos yra nuoroda iš %s',
    'nl': u'Bot: verwijdert alle pagina\'s met een link op %s',
    'pl': u'Robot usuwa wszystkie artykuły zlinkowane z %s',
    'pt': u'Bot: Apagando todas as páginas ligadas a %s',
}
msg_delete_ref = {
    'de': u'Bot: Lösche alle auf %s linkenden Seiten',
    'en': u'Robot - Deleting all pages referring from %s',
    'fr': u'Bot: Supprime toutes pages référant à %s',
    'he': u'בוט: מוחק את כל הדפים המקשרים לדף %s.',
    'lt': u'robotas: Trinami visi puslapiai rodantys į %s',
    'nl': u'Bot: verwijdert alle pagina\'s met referentie van %s',
    'pl': u'Robot usuwa wszystkie artykuły odnoszące się do %s',
    'pt': u'Bot: Apagando todas as páginas afluentes a %s',
}
msg_delete_images = {
    'en': u'Robot - Deleting all images on page %s',
    'he': u'בוט: מוחק את כל התמונות בדף %s.',
    'nl': u'Bot: verwijdert alle media op pagina %s',
    'pl': u'Robot usuwa wszystkie obrazy w artykule %s',
    'pt': u'Bot: Apagando todas as imagens da página %s',
}

class DeletionRobot:
    """
    This robot allows deletion of pages en masse.
    """

    def __init__(self, generator, summary, always = False, undelete=True):
        """
        Arguments:
            * generator - A page generator.
            * always - Delete without prompting?
        """
        self.generator = generator
        self.summary = summary
        self.always = always
        self.undelete = undelete

    def run(self):
        """
        Starts the robot's action.
        """
        #Loop through everything in the page generator and delete it.
        for page in self.generator:
            wikipedia.output(u'Processing page %s' % page.title())
            if self.undelete:
                page.undelete(self.summary, throttle = True)
            else:
                page.delete(self.summary, not self.always, throttle = True)

def main():
    pageName = ''
    singlePage = ''
    summary = ''
    always = False
    doSinglePage = False
    doCategory = False
    deleteSubcategories = True
    doRef = False
    doLinks = False
    doImages = False
    undelete = False
    fileName = ''
    gen = None

    # read command line parameters
    for arg in wikipedia.handleArgs():
        if arg == '-always':
            always = True
        elif arg.startswith('-file'):
            if len(arg) == len('-file'):
                fileName = wikipedia.input(u'Enter name of file to delete pages from:')
            else:
                fileName = arg[len('-file:'):]
        elif arg.startswith('-summary'):
            if len(arg) == len('-summary'):
                summary = wikipedia.input(u'Enter a reason for the deletion:')
            else:
                summary = arg[len('-summary:'):]
        elif arg.startswith('-cat'):
            doCategory = True
            if len(arg) == len('-cat'):
                pageName = wikipedia.input(u'Enter the category to delete from:')
            else:
                pageName = arg[len('-cat:'):]
        elif arg.startswith('-nosubcats'):
            deleteSubcategories = False
        elif arg.startswith('-links'):
            doLinks = True
            if len(arg) == len('-links'):
                pageName = wikipedia.input(u'Enter the page to delete from:')
            else:
                pageName = arg[len('-links:'):]
        elif arg.startswith('-ref'):
            doRef = True
            if len(arg) == len('-ref'):
                pageName = wikipedia.input(u'Enter the page to delete from:')
            else:
                pageName = arg[len('-ref:'):]
        elif arg.startswith('-page'):
            doSinglePage = True
            if len(arg) == len('-page'):
                pageName = wikipedia.input(u'Enter the page to delete:')
            else:
                pageName = arg[len('-page:'):]
        elif arg.startswith('-images'):
            doImages = True
            if len(arg) == len('-images'):
                pageName = wikipedia.input(u'Enter the page with the images to delete:')
            else:
                pageName = arg[len('-images'):]
        elif arg.startswith('-undelete'):
            undelete = True

    mysite = wikipedia.getSite()

    if doSinglePage:
        if not summary:
            summary = wikipedia.input(u'Enter a reason for the deletion:')
        page = wikipedia.Page(mysite, pageName)
        gen = iter([page])
    elif doCategory:
        if not summary:
            summary = wikipedia.translate(mysite, msg_delete_category) % pageName
        ns = mysite.category_namespace()
        categoryPage = catlib.Category(mysite, ns + ':' + pageName)
        gen = pagegenerators.CategorizedPageGenerator(categoryPage, recurse = deleteSubcategories)
    elif doLinks:
        if not summary:
            summary = wikipedia.translate(mysite, msg_delete_links) % pageName
        wikipedia.setAction(summary)
        linksPage = wikipedia.Page(mysite, pageName)
        gen = pagegenerators.LinkedPageGenerator(linksPage)
    elif doRef:
        if not summary:
            summary = wikipedia.translate(mysite, msg_delete_ref) % pageName
        refPage = wikipedia.Page(mysite, pageName)
        gen = pagegenerators.ReferringPageGenerator(refPage)
    elif fileName:
        if not summary:
            summary = wikipedia.translate(mysite, msg_simple_delete)
        gen = pagegenerators.TextfilePageGenerator(fileName)
    elif doImages:
        if not summary:
            summary = wikipedia.translate(mysite, msg_delete_images)
        gen = pagegenerators.ImagesPageGenerator(wikipedia.Page(mysite, pageName))

    if gen:
        wikipedia.setAction(summary)
        # We are just deleting pages, so we have no need of using a preloading page generator
        # to actually get the text of those pages.
        bot = DeletionRobot(gen, summary, always, undelete)
        bot.run()
    else:
        wikipedia.showHelp(u'delete')

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
