def percentage_liked(controller_dict, segment_size):
    """
    Controller dictionary should be in the following format:
        {client_id : time / None}
            in which time shows how much time (in seconds) after the latest
            transition the client left the channel. If the client_id is still
            on the channel, time = None.
    """
    total = 0
    on_channel = 0
    channel_switches = 0
    for _, time in controller_dict.items():
        total += 1

        if time is None:
            on_channel += 1
        else if time > 1:
            channel_switches += 1 / (time + 1/9) + 0.1

    return (total - channel_switches) / total
