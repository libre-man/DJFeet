# -*- coding: utf-8 -*-
from .helpers import SongStruct


class Transitioner:
    def __init__(self):
        pass

    def merge(self, prev_song, next_song):
        """Merge the two given song structs.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")

    def write_sample(self, sample):
        """Write the given sample to the output stream.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")
