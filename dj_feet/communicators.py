# -*- coding: utf-8 -*-
import requests

from .helpers import SongStruct


class Communicator:
    def __init__(self):
        pass

    def get_user_feedback(self, remote, controller_id, start, end):
        """Get and return the user feedback. The return value should be
        subtyping dict"""
        raise NotImplementedError("This method should be overridden")


class SimpleCommunicator(Communicator):
    def __init__(self):
        pass

    def get_user_feedback(self, remote, controller_id, start, end):
        return {}


class ProtocolCommunicator(Communicator):
    def __init__(self):
        pass

    def get_user_feedback(self, remote, controller_id, start, end):
        res = requests.post(remote + '/get_feedback/',
                            json={
                                'start': start,
                                'end': end,
                                'id': controller_id,
                            })
        return res.json()['feedback']
