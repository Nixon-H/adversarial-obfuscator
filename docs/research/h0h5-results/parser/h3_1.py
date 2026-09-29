import sys

def _nx_385816(text):
    _nixon_ぺნञҐๆӶɒѬ = []
    for _nixon_בɣǏ崜ؕ柭ɬᚯȎჩ in text.lower():
        if _nixon_בɣǏ崜ؕ柭ɬᚯȎჩ.isalnum():
            _nixon_ぺნञҐๆӶɒѬ.append(_nixon_בɣǏ崜ؕ柭ɬᚯȎჩ)
        elif _nixon_ぺნञҐๆӶɒѬ and _nixon_ぺნञҐๆӶɒѬ[-1] != '-':
            _nixon_ぺნञҐๆӶɒѬ.append('-')
    return ''.join(_nixon_ぺნञҐๆӶɒѬ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_خุطɓՆᏬƈᛓड़ƿ = argv[0]
    _nixon_ฦɖศᎼᏲᛨʧぶฤঊ = ' '.join(argv[1:])
    if _nixon_خุطɓՆᏬƈᛓड़ƿ == 'slugify':
        print(_nx_385816(_nixon_ฦɖศᎼᏲᛨʧぶฤঊ))
    elif _nixon_خุطɓՆᏬƈᛓड़ƿ == 'count_words':
        print(_nx_385101(_nixon_ฦɖศᎼᏲᛨʧぶฤঊ))
    elif _nixon_خุطɓՆᏬƈᛓड़ƿ == 'reverse_words':
        print(_nx_31b169(_nixon_ฦɖศᎼᏲᛨʧぶฤঊ))
    elif _nixon_خุطɓՆᏬƈᛓड़ƿ == 'shout':
        print(_nx_8ca8c6(_nixon_ฦɖศᎼᏲᛨʧぶฤঊ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])