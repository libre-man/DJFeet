#!/usr/bin/env python3

import logging
import sys

if 'test' not in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.ERROR)
