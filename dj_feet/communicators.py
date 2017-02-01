# -*- coding: utf-8 -*-
import requests
import os

from .helpers import SongStruct


class Communicator:
    def __init__(self):
        pass

    def get_user_feedback(self, remote, controller_id, start, end):
        """Get and return the user feedback. The return value should be
        subtyping dict"""
        raise NotImplementedError("This method should be overridden")

    def iteration(self, remote, controller_id, mixed):
        """Do the iteration request to a server or let the user know
        something."""
        raise NotImplementedError("This method should be overridden")


class SimpleCommunicator(Communicator):
    def __init__(self):
        pass

    def get_user_feedback(self, remote, controller_id, start, end):
        return {}

    def iteration(self, remote, controller_id, mixed):
        pass


class ProtocolCommunicator(Communicator):
    def __init__(self):
        pass

    def get_user_feedback(self, remote, controller_id, start, end):
        res = requests.post(
            remote + '/get_feedback/',
            json={
                'start': start,
                'end': end,
                'id': controller_id,
            })
        return res.json()['feedback']

    def iteration(self, remote, controller_id, mixed):
        requests.post(
            remote + '/iteration/',
            json={
                'filename_mixed':
                os.path.splitext(os.path.basename(mixed.file_location))[0],
                'id': controller_id
            })
