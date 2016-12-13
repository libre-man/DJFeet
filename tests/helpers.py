import os
import pytest

EPSILON = 0.000000001


class MockingFunction():
    def __init__(self, func=None, simple=False, pack=False, amount=False):
        self.called = False
        self.args = list()
        self.func = func
        self.simple = simple
        self.pack = pack
        self.amount = amount
        self._amount = 0

    def __call__(self, *args, **kwargs):
        self.called = True
        self.args.append((args, kwargs))
        self._amount += 1
        if self.func is not None:
            if self.simple:
                return self.func()
            elif self.pack:
                return self.func(args)
            elif self.amount:
                return self.func(self._amount)
            else:
                return self.func(*args, **kwargs)
