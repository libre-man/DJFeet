# -*- coding: utf-8 -*-
import sys
import time


def loop(controller, picker, transitioner, communicator):
    if not controller.should_continue():
        return
    new_sample = None
    old_sample = picker.get_next_song(None)
    transitioner.write(transitioner.merge(None, old_sample))
    while controller.should_continue():
        new_sample = picker.get_next_song(communicator.get_user_feedback())
        transitioner.write(transitioner.merge(old_sample, new_sample))
        sleep_time = controller.waittime(new_sample)
        if sleep_time < 0:
            print('Sleep time is negative, not enough samples!',
                  file=sys.stderr)
        else:
            time.sleep(sleep_time)
        old_sample = new_sample
