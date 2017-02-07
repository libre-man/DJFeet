# -*- coding: utf-8 -*-

import datetime


class Controller:
    """This is the base Controller class.

    You should not use this class directly but should inherit from this class
    if you want to implement a new picker. A subclass should override all
    public methods of this class.
    """

    def should_continue(self):
        """Return if the loop should continue.

        This function does not have to be pure and only gets called once every
        core iteration. This is guaranteed and it is called before
        :func:`get_waittime` is called.

        :returns: If we should continue with the core loop.
        :rtype: bool
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")

    def get_waittime(self, epoch, segment_size):
        """Return the amount of time we should sleep for.

        This can be negative, however this negative time will NOT be corrected
        for next loop. This function should do this.

        :param float epoch: The unix time stamp we started,
                            see :mod:`dj_feet.core` for more information.
        :param int segment_size: The size of each generated segment.
        :returns: The amount of time the core looper should sleep.
        :rtype: numbers.Number
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
        """
        :param int iteration_amount: The amount of iterations to do, and
                                     therefore also the amount of samples to
                                     generate.
        """
        self.iteration_amount = iteration_amount
        self.iterations_done = 0

    def should_continue(self):
        """Checks if we should do another iteration of the core loop.

        .. note:: This adjusts the :attr:`self.iterations_done` variable, so
                  this function is not pure.

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
