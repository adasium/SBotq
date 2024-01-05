import pendulum

from bernardynki import Bernardynki


def test_first():
    b = Bernardynki.first
    assert b.when.date() == pendulum.DateTime(2022, 1, 16).date()
    assert b.count == 1
    assert b.great


def test_next_bernardynki():
    b = Bernardynki.first
    b += 1
    assert b.when.date() == pendulum.DateTime(2022, 2, 17).date()
    assert b.count == 2
    assert not b.great


def test_great_bernardynki():
    b = Bernardynki.first
    b += 25

    assert b.when.date() == pendulum.DateTime(2024, 3, 13).date()
    assert b.count == 26
    assert b.great


def test_next_after():
    after = pendulum.DateTime(2024, 3, 12)
    b = Bernardynki.next_after(after)

    assert b.when.date() == pendulum.DateTime(2024, 3, 13).date()
    assert b.count == 26
    assert b.great
