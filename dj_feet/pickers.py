# -*- coding: utf-8 -*-

from .helpers import SongStruct


class Picker:
    def __init__(self):
        pass

    def get_next_song(self, user_feedback):
        """Return a SongStruct for the next song that should be used"""
        raise NotImplementedError("This should be overridden")
