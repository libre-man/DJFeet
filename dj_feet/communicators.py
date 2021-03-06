# -*- coding: utf-8 -*-
import requests
import os

from .helpers import SongStruct


class Communicator:
    """This is the base Communicator class.

    You should not use this class directly but should inherit from this class
    if you want to implement a new picker. A subclass should override all
    public methods of this class.
    """

    def get_user_feedback(self, remote, controller_id, start, end):
        """Get and return the user feedback. The return value should be
        subtyping dict.

        :param string remote: The http address of the remote including http
        :param controller_id: The id of the current controller
        :param int start: The start time to request the feedback from
        :param int end: The end time to request the feedback from
        :returns: A dictionary containing the received feedback.
        :rtype: dict
        """
        raise NotImplementedError("This method should be overridden")

    def iteration(self, remote, controller_id, mixed):
        """Do the iteration request to a server or let the user know
        something.

        :param str remote: This is ignored.
        :param int controller_id: The id of this controller.
        :param str mixed: The name of the file mixed without the extension.
        :returns: Nothing of value.
        :rtype: None
        """
        raise NotImplementedError("This method should be overridden")


class SimpleCommunicator(Communicator):
    """A simple communicator that does not conform to the standard protocol.

    This picker is a simple proof of concept, it however does not conform to
    the :ref:`#sdaas protocol<sdaas-protocol>` so you will miss some data in
    your overview and feedback WON'T work. All data returned is static.
    """

    def __init__(self):
        super(SimpleCommunicator, self).__init__()

    def get_user_feedback(self, remote, controller_id, start, end):
        """Simply always return an empty dictionary as if there was no
        feedback.

        :param string remote: The http address of the remote including http
        :param controller_id: The id of the current controller
        :param int start: The start time to request the feedback from
        :param int end: The end time to request the feedback from
        :returns: A empty dictionary
        :rtype: dict
        """
        return {}

    def iteration(self, remote, controller_id, mixed):
        """This does nothing useful whatsoever.

        :param str remote: This is ignored.
        :param int controller_id: The id of this controller.
        :param str mixed: The name of the file mixed without the extension.
        :returns: Nothing of value.
        :rtype: None
        """
        pass


class ProtocolCommunicator(Communicator):
    """A communicator that conforms to the #sdaas protocol.

    This means it does a POST request to '/iteration/' on every iteration and
    gets feedback by doing a POST request to '/get_feedback' including the
    required information.
    """

    def __init__(self):
        super(ProtocolCommunicator, self).__init__()

    def get_user_feedback(self, remote, controller_id, start, end):
        """Perform a POST request to '/get_feedback'.

        .. note:: This call is blocking: this means it waits till the remote as
                  replied.

        :param string remote: The http address of the remote including http
        :param controller_id: The id of the current controller
        :param int start: The start time to request the feedback from
        :param int end: The end time to request the feedback from
        :returns: The 'feedback' key from the returned dictionary from the
                  server
        :rtype: dict
        """
        res = requests.post(
            remote + '/get_feedback/',
            json={
                'start': start,
                'end': end,
                'id': controller_id,
            })
        return res.json()['feedback']

    def iteration(self, remote, controller_id, mixed):
        """Do a iteration request to the remote.

        .. note:: This call is blocking: this means it waits till the remote as
                  replied.

        :param string remote: The http address of the remote including http
        :param controller_id: The id of the current controller
        :param string mixed: The filename without extension of the song mixed.
        :returns: Nothing of value
        """
        requests.post(
            remote + '/iteration/',
            json={
                'filename_mixed':
                os.path.splitext(os.path.basename(mixed.file_location))[0],
                'id': controller_id
            })
