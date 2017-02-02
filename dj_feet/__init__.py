#!/usr/bin/env python3

import logging
import sys

if 'test' not in sys.argv:
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s' +
        ':%(module)s::%(funcName)s: %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S")
else:
    logging.basicConfig(level=logging.ERROR)
