# -*- coding: utf-8 -*-

from .helpers import SongStruct
import os
import random


class Picker:
    def __init__(self):
        pass

    def get_next_song(self, user_feedback):
        """Return a SongStruct for the next song that should be used"""
        raise NotImplementedError("This should be overridden")


class SimplePicker(Picker):
    def __init__(self, song_folder):
        self.song_folder = song_folder
        self.song_files = [f for _, __, f in os.walk(song_folder)][0]

    def get_next_song(self, user_feedback):
        next_song = ""
        while not os.path.isfile(os.path.join(self.song_folder, next_song)):
            if not self.song_files:
                raise ValueError("There are no songs left")
            next_song = random.choice(self.song_files)
            self.song_files.remove(next_song)
        return SongStruct(next_song, 0, -1)
