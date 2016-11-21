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

    def get_waittime(self, prev_sample):
        """Return the amount of time we should sleep for.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")


class SimpleController(Controller):
    def __init__(self, iteration_amount, ssc_delta):
        self.iteration_amount = iteration_amount
        self.iterations_done = 0
        self.previous_time = None
        self.ssc_delta = ssc_delta

    def should_continue(self):
        self.iterations_done += 1
        return self.iteration_amount >= self.iterations_done

    def get_waittime(self, prev_sample):
        if self.previous_time is None:
            self.previous_time = datetime.datetime.now()
            return 0
        now = datetime.datetime.now()
        res = self.ssc_delta - (now - self.previous_time).total_seconds()
        self.previous_time = now
        return max(res, 0)
