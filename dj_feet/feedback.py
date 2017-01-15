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
        if time is not None and time > 1:
            channel_switches += 1 / (time + (1 / 9)) + 0.1
            total += 1

    return (total - channel_switches) / total
