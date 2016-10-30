import pytest
import os
import sys

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.cli as cli


@pytest.mark.parametrize("debug", [True, False])
def test_main(debug):
    cli.main(debug=debug)
