# -*- coding: utf-8 -*-

import datetime


class Controller:
    def __init__(self):
        pass

    def should_continue(self):
        """Return if the loop should continue.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")

    def get_waittime(self, epoch, segment_size):
        """Return the amount of time we should sleep for.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")


class SimpleController(Controller):
    def __init__(self, iteration_amount):
        self.iteration_amount = iteration_amount
        self.iterations_done = 0

    def should_continue(self):
        self.iterations_done += 1
        return self.iteration_amount >= self.iterations_done

    def get_waittime(self, epoch, segment_size):
        now = datetime.datetime.now().timestamp()
        res = (segment_size * self.iterations_done + epoch) - now
        return res
