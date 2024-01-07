import pytest
from parametrization import Parametrization

import diffle


@pytest.fixture
def one_word_dict():
    d = [
        'niedowierzanie',
    ]
    yield d


def test_exact_match():
    solver = diffle.Solver(diffle.DICT)
    solver.guess('[niedowierzanie]')
    matches = solver.get_matches(polish=False)
    assert matches == ['niedowierzanie']


@Parametrization.autodetect_parameters()
@Parametrization.case(name='exact_match', guess='[niedowierzanie]')
@Parametrization.case(name='right_anchor', guess='(dowierzanie]')
@Parametrization.case(name='patchy_right_anchor', guess='(d)(anie]')
@Parametrization.case(name='left_anchor', guess='[niedowierza)')
def test_one_match(one_word_dict, guess):
    solver = diffle.Solver(one_word_dict)
    solver.guess(guess)
    matches = solver.get_matches(polish=False)
    assert matches == ['niedowierzanie']


@Parametrization.autodetect_parameters()
@Parametrization.case(name='yellow', guess='(r)(a)Z')
def test_yellow(one_word_dict, guess):
    solver = diffle.Solver(one_word_dict)
    solver.guess(guess)
    matches = solver.get_matches(polish=False)
    assert matches == ['niedowierzanie']
