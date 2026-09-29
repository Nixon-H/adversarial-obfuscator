import sys

def _nx_385816(text):
    _nixon_Ꭼ嬴חרϒֈ = []
    for _nixon_৮ৠٚ鞠つϑɻڠƿ in text.lower():
        if _nixon_৮ৠٚ鞠つϑɻڠƿ.isalnum():
            _nixon_Ꭼ嬴חרϒֈ.append(_nixon_৮ৠٚ鞠つϑɻڠƿ)
        elif _nixon_Ꭼ嬴חרϒֈ and _nixon_Ꭼ嬴חרϒֈ[-1] != '-':
            _nixon_Ꭼ嬴חרϒֈ.append('-')
    return ''.join(_nixon_Ꭼ嬴חרϒֈ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ѓॗऴۖҥƂ = argv[0]
    _nixon_ฑϐऱʂႰ = ' '.join(argv[1:])
    if _nixon_ѓॗऴۖҥƂ == 'slugify':
        print(_nx_385816(_nixon_ฑϐऱʂႰ))
    elif _nixon_ѓॗऴۖҥƂ == 'count_words':
        print(_nx_385101(_nixon_ฑϐऱʂႰ))
    elif _nixon_ѓॗऴۖҥƂ == 'reverse_words':
        print(_nx_31b169(_nixon_ฑϐऱʂႰ))
    elif _nixon_ѓॗऴۖҥƂ == 'shout':
        print(_nx_8ca8c6(_nixon_ฑϐऱʂႰ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])