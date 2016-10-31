# -*- coding: utf-8 -*-


class Controller:
    def __init__(self):
        pass

    def should_continue(self):
        """Return if the loop should continue.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")

    def get_waittime(self, prev_sample):
        """Return the amount of time we should sleep for.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")
