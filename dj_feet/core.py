# -*- coding: utf-8 -*-
import sys
import time
import requests
import logging

l = logging.getLogger(__name__)


def loop(app_id, remote, controller, picker, transitioner, communicator):
    merge_times = []
    new_sample = None
    old_sample = None
    segment_size = None
    i = 0  # The part we are generating
    l.debug("Starting core loop.")

    while controller.should_continue():
        if len(merge_times) == 4:
            l.debug('Getting feedback from the communicator.')
            start, end = merge_times.pop(0)
            feedback = communicator.get_user_feedback(remote, app_id, start,
                                                      end)
            l.debug('Received feedback from the server: %s.', feedback)
        else:
            l.debug('Not enough samples yet, so got no feedback.')
            feedback = {}

        l.debug("Starting picking.")
        new_sample = picker.get_next_song(feedback, force=False)
        l.info("Got song: %s.", new_sample.file_location)
        while True:
            try:
                result, merge_offset = transitioner.merge(old_sample,
                                                          new_sample)
                break
            except ValueError:
                l.info('Got song %s however' +
                       ' this was not good, trying with force',
                       new_sample.file_location)
                new_sample = picker.get_next_song(feedback, force=True)

        l.debug("Appending succeeded. Continuing")

        if merge_times:
            # First update the previous segment with an ending time
            merge_times[-1].append(segment_size * i + merge_offset)

            # Now insert the starting time of the new segment
            merge_times.append([segment_size * i + merge_offset])
        else:
            requests.post(
                remote + "/controller_started/",
                json={
                    'id': app_id,
                    'epoch': int(time.time()),
                })
            merge_times.append([0])
            segment_size = merge_offset

        l.info("Writing result to output.")
        transitioner.write_sample(result)
        l.debug("Wrote to output.")

        l.info("Letting the communicator know we did an iteration.")
        communicator.iteration(remote, app_id, new_sample)

        sleep_time = controller.get_waittime(new_sample)
        l.info('Going to sleep for %f seconds', sleep_time)
        if sleep_time < 0:
            l.error('Sleep time is negative, not enough samples!')
        else:
            time.sleep(sleep_time)
        controller.reset_sleeptime()

        old_sample = new_sample
        i += 1
    l.debug("Ended our core loop! We are terminating.")
