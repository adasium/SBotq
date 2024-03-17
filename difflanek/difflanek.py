import os
import re
from collections import Counter

import numpy as np

def get_valid_words(words: list[str], is_polish_word: bool) -> list[str]:
    """
        jak wpisywać słowa:
           szary - x
           żółty - X
           zielony:
               pojedyncze litery - (x)
               sekwencje - (xyz)
               poprawny początek/koniec słowa - [x)yzx(yz]
    """

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pl_PL.dic')
    with open(path, encoding='iso-8859-2') as file:
        length = int(file.readline()) + 9
        dictionary = np.empty(length, dtype=object)
        for i in range(length):
            dictionary[i] = file.readline().split('/', 1)[0].rstrip('\n')

    isPolishValid = is_polish_word

    polish = 'ąćęłńóśźż'
    invalid = f'A-Z{polish.upper()}' + ('' if isPolishValid else polish)
    regex = ''

    for word in words:
        gray = []
        yellow = []
        green = []

        border = word[0]
        heavyBorder = (border == '[')
        isGreenzone = (border == '(') or heavyBorder
        if isGreenzone:
            word = word[1:]

        template = '(?=^'
        if isGreenzone and not heavyBorder:
            template += '[^{grayNoYellows}' + word[0] + '][^{grayNoYellows}]*'
        yellowzone = ''
        isYellowzone = not isGreenzone

        for letter in word:
            if isGreenzone:
                if letter == ')' or letter == ']':
                    yellowzone = ''
                    isGreenzone = False
                else:
                    green += letter
                    template += letter
            else:
                if letter == '(':
                    template += '[^{grayNoYellows}' + yellowzone + ']' + ('*' if isYellowzone else '+')
                    isGreenzone = True
                    isYellowzone = False
                else:
                    if re.search(f'[a-z{polish}]', letter) and letter not in gray:
                        gray += letter
                    if re.search(f'[A-Z{polish.upper()}]', letter):
                        yellow += letter.lower()
                        yellowzone += letter.lower()
                    isYellowzone = True


        border = word[-1]
        heavyBorder = (border == ']')
        isGreenzone = (border == ')') or heavyBorder
        if isGreenzone:
            if not heavyBorder:
                template += '[^{grayNoYellows}]*[^{grayNoYellows}' + word[-2] + ']'
        else:
            template += '[^{grayNoYellows}' + yellowzone + ']*'
        template += '$)'

        grayNoYellows = [letter for letter in gray if letter not in yellow]
        grayNoOthers = [letter for letter in grayNoYellows if letter not in green]
        if not yellow or ')' in word or ']' in word:
            regex += template.format(grayNoYellows= invalid + ''.join(grayNoYellows))

        for letter, count in Counter(yellow + green).items():
            if letter in yellow:
                knownCount = letter in gray
                template = '(?=^'
                for i in range(count):
                    template += '[^{grayNoOthers}' + (letter if knownCount else '') + ']*' + letter
                template += '[^{grayNoOthers}' + (letter if knownCount else '') + ']*$)'
                regex += template.format(grayNoOthers= invalid + ''.join(grayNoOthers))

        if isPolishValid:
            regex += f'(?=^[^{invalid}]*[{polish}]+[^{invalid}]*$)'

    answers = sorted(filter(lambda word: re.search(regex, word), dictionary), key=len)

    return answers
