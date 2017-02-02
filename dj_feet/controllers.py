# -*- coding: utf-8 -*-

import datetime


class Controller:
    """The base Controller class.

    This class is only used for configuration purposes and EVERY method should
    be overwritten.
    """

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
    """A simple controller that uses a fixed amount of iterations.

    The time to sleep is calculated by using the start epoch. This is a robust
    controller that does not do any networking and has a fixed amount of
    iterations.
    """

    def __init__(self, iteration_amount):
        """Initialize a `SimpleController` object.

        :param int iteration_amount: The amount of iterations, and therefore
                                     the amount of samples to generate, to do.
        """
        self.iteration_amount = iteration_amount
        self.iterations_done = 0

    def should_continue(self):
        """Checks if we should do another iteration of the core loop.

        This adjusts the `self.iterations_done` variable, so this function is
        NOT pure.
        :returns: If we should do a next iteration.
        :rtype: int
        """
        self.iterations_done += 1
        return self.iteration_amount >= self.iterations_done

    def get_waittime(self, epoch, segment_size):
        """Get the amount of time in seconds we should sleep before the next
        iteration.

        This is calculated by taking the current time and subtracting
        segment_size * iterations_done plus epoch from it. This means that if
        we encounter a negative sleep time (we were too slow) we can adjust
        this on the next iteration by sleeping less.

        :param float epoch: The unix timestamp of the moment the controller had
                            created its first segment.
        :param int segment_size: The length of a single segment in seconds.
        :returns: The time in seconds we should sleep.
        :rtype: float
        """
        now = datetime.datetime.now().timestamp()
        res = (segment_size * self.iterations_done + epoch) - now
        return res
