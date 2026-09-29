import sys

def _nx_385816(text):
    _nixon_άᏬԺঢ়ɸど縤ᛤŎע = []
    for _nixon_षৼדᏳᛞ in text.lower():
        if _nixon_षৼדᏳᛞ.isalnum():
            _nixon_άᏬԺঢ়ɸど縤ᛤŎע.append(_nixon_षৼדᏳᛞ)
        elif _nixon_άᏬԺঢ়ɸど縤ᛤŎע and _nixon_άᏬԺঢ়ɸど縤ᛤŎע[-1] != '-':
            _nixon_άᏬԺঢ়ɸど縤ᛤŎע.append('-')
    return ''.join(_nixon_άᏬԺঢ়ɸど縤ᛤŎע).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ΎцॿǗႾۅᚮि顡ᚠ = argv[0]
    _nixon_Ⴅ腊इ逘ėজ = ' '.join(argv[1:])
    if _nixon_ΎцॿǗႾۅᚮि顡ᚠ == 'slugify':
        print(_nx_385816(_nixon_Ⴅ腊इ逘ėজ))
    elif _nixon_ΎцॿǗႾۅᚮि顡ᚠ == 'count_words':
        print(_nx_385101(_nixon_Ⴅ腊इ逘ėজ))
    elif _nixon_ΎцॿǗႾۅᚮि顡ᚠ == 'reverse_words':
        print(_nx_31b169(_nixon_Ⴅ腊इ逘ėজ))
    elif _nixon_ΎцॿǗႾۅᚮि顡ᚠ == 'shout':
        print(_nx_8ca8c6(_nixon_Ⴅ腊इ逘ėজ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])