# -*- coding: utf-8 -*-
import random


def feedback_default(_):
    """This does nothing with the user feedback and simply returns a random
    float between 0 and 1.
    """
    return random.random()


def feedback_percentage_liked(controller_dict):
    """
    Controller dictionary should be in the following format:
        {feedback: {client_id : time / None}}
            in which time shows how much time (in seconds) after the latest
            transition the client left the channel. If the client_id is still
            on the channel, time = None.
    """
    total = 0
    channel_switches = 0

    for _, time in controller_dict['feedback'].items():
        # We ignore all people that left the channel within 1 second of our
        # merge as they did not react to this merge in our opinion.
        if time is None:
            total += 1
        if time is not None and time >= 1:
            channel_switches += 1 / (float(time) + (1 / 9)) + 0.1
            total += 1

    # If nobody is on the channel we simply think we are doing awesome.
    if total == 0:
        return 1

    return (total - channel_switches) / total
