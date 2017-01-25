# -*- coding: utf-8 -*-
import sys
import time
import requests


def loop(app_id, remote, controller, picker, transitioner, communicator):
    merge_times = []
    new_sample = None
    old_sample = None
    segment_size = None
    i = 0  # The part we are generating
    print("Starting core loop")

    while controller.should_continue():
        if len(merge_times) == 4:
            start, end = merge_times.pop(0)
            feedback = communicator.get_user_feedback(start, end)
        else:
            feedback = {}

        print("Starting picking")
        new_sample = picker.get_next_song(feedback, force=False)
        print("Got song: {}".format(new_sample))
        while True:
            try:
                result, merge_offset = transitioner.merge(old_sample,
                                                          new_sample)
                break
            except ValueError:
                print('Trying with some FORCE!')
                new_sample = picker.get_next_song(feedback, force=True)

        print("Appending succeeded. Continuing")

        if merge_times:
            # First update the previous segment with an ending time
            merge_times[-1].append(segment_size * i + merge_offset)

            # Now insert the starting time of the new segment
            merge_times.append([merge_offset])
        else:
            requests.post(
                remote + "/controller_started/",
                data={
                    'id': app_id,
                    'epoch': int(time.time())
                })
            merge_times.append([0])
            segment_size = merge_offset

        print("Trying to write to output")
        transitioner.write_sample(result)
        print("Wrote to output")

        sleep_time = controller.get_waittime(new_sample)
        print('Going to sleep for {} seconds'.format(sleep_time))
        if sleep_time < 0:
            print(
                'Sleep time is negative, not enough samples!', file=sys.stderr)
        else:
            time.sleep(sleep_time)

        old_sample = new_sample
        i += 1
    print("Ended our core loop!")
