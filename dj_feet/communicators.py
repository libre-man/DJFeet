# -*- coding: utf-8 -*-

from .helpers import SongStruct


class Communicator:
    def __init__(self):
        pass

    def get_user_feedback(self):
        """Get and return the user feedback. The return value should be
        subtyping dict"""
        raise NotImplementedError("This method should be overridden")
