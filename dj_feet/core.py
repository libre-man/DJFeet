# -*- coding: utf-8 -*-
import sys
import time
import requests
import logging

l = logging.getLogger(__name__)


def loop(app_id, remote, controller, picker, transitioner, communicator):
    """The core looper used by DJFeet while generating music.

    This generates music as long as it is indicated by the controller to do so.
    It connects all the different parts of #sdaas.

    :param int app_id: The id of this controller.
    :param str remote: The web address of the remote including `http` or `https`.
    :param Controller controller: The controller to use for this loop.
    :param Picker picker: The picker to use for this loop.
    :param Transitioner transitioner: The transitioner to use for this loop.
    :param Communicator communicator: The communicator to use for this loop.
    :raises Exception: If anything goes wrong which we can't recover from this
                       exception is bubbled up.
    :returns: Nothing of value.
    :rtype: None
    """
    merge_times = []
    new_sample = None
    old_sample = None
    segment_size = None
    i = 0  # The part we are generating
    epoch = None
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
            epoch = time.time()
            requests.post(
                remote + "/controller_started/",
                json={
                    'id': app_id,
                    'epoch': round(epoch),
                })
            merge_times.append([0])
            segment_size = merge_offset

        l.info("Writing result to output.")
        transitioner.write_sample(result)
        l.debug("Wrote to output.")

        sleep_time = controller.get_waittime(epoch, segment_size)
        l.info('Going to sleep for %f seconds', sleep_time)
        if sleep_time < 0:
            l.error('Sleep time is negative, not enough samples!')
        else:
            time.sleep(sleep_time)

        l.info("Letting the communicator know we did an iteration.")
        communicator.iteration(remote, app_id, new_sample)

        old_sample = new_sample
        i += 1
    l.debug("Ended our core loop! We are terminating.")
