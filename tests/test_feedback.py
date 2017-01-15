import os
import sys
from types import FunctionType
from numbers import Number
from helpers import EPSILON
import pytest

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.feedback as f


@pytest.mark.parametrize("feedback,expected",
                         [({0: 0}, 1),
                          ({0: 1}, 0),
                          ({0: 1, 1: None}, 1 / 2),
                          ({0: 1, 1: 2, 2: None}, lambda x: x > 1 / 3),
                          ({0: 1, 1: 1, 2: None}, 1 / 3),
                          (5, AttributeError),
                          ({0: '1'}, TypeError)])
def test_feedback_percentage_liked(feedback, expected):
    if isinstance(expected, Number) or isinstance(expected, FunctionType):
        got = f.feedback_percentage_liked({'feedback': feedback})
        if callable(expected):
            assert expected(got)
        else:
            assert abs(got - expected) < EPSILON
    else:
        with pytest.raises(expected):
            got = f.feedback_percentage_liked({'feedback': feedback})
