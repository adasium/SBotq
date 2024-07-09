from datetime import time

import pendulum
import pytest

from utils import next_call_timestamp


@pytest.mark.parametrize(
    'now,scheduled_at,scheduled_every,expected',
    [
        (
            pendulum.datetime(2024, 1, 5, 21, 54, tz=pendulum.UTC),
            time(21, 55),
            pendulum.duration(days=1),
            pendulum.datetime(2024, 1, 5, 21, 55, tz=pendulum.UTC),
        ),
    ],
)
def test_next_call_timestamp(now, scheduled_at, scheduled_every, expected):
    result = next_call_timestamp(now, scheduled_at, scheduled_every)
    assert result == expected
