# -*- coding: utf-8 -*-
import sys
import time


def loop(controller, picker, transitioner, communicator):
    merge_times = []
    new_sample = None
    old_sample = None
    segment_size = None
    i = 0  # The part we are generating

    while controller.should_continue():
        if len(merge_times) == 4:
            start, end = merge_times.pop(0)
            feedback = communicator.get_user_feedback(start, end)
        else:
            feedback = {}

        new_sample = picker.get_next_song(feedback, force=False)
        while True:
            try:
                result, merge_offset = transitioner.merge(old_sample,
                                                          new_sample)
                break
            except ValueError:
                new_sample = picker.get_next_song(feedback, force=True)

        if merge_times:
            # First update the previous segment with an ending time
            merge_times[-1].append(segment_size * i + merge_offset)

            # Now insert the starting time of the new segment
            merge_times.append([merge_offset])
        else:
            merge_times.append([0])
            segment_size = merge_offset

        transitioner.write(result)

        sleep_time = controller.waittime(new_sample)
        if sleep_time < 0:
            print(
                'Sleep time is negative, not enough samples!', file=sys.stderr)
        else:
            time.sleep(sleep_time)

        old_sample = new_sample
        i += 1
