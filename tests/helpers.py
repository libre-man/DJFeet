import os
import pytest


class MockingFunction():
    def __init__(self, func=None, simple=False, pack=False):
        self.called = False
        self.args = list()
        self.func = func
        self.simple = simple
        self.pack = pack

    def __call__(self, *args, **kwargs):
        self.called = True
        self.args.append((args, kwargs))
        if self.func is not None:
            if self.simple:
                return self.func()
            elif self.pack:
                return self.func(args)
            else:
                return self.func(*args, **kwargs)
