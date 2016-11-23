# -*- coding: utf-8 -*-

from .helpers import SongStruct
from collections import defaultdict
import os
import random
import librosa
import numpy


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
        return SongStruct(next_song, 0, None)


class NCAPicker(Picker):
    def __init__(self, song_folder, mfcc_amount=20, current_multiplier=0.5):
        self.current_song = None
        self.multiplier = current_multiplier
        self.streak = 0

        self.song_folder = song_folder
        self.song_files = [f for _, __, f in os.walk(song_folder)][0]

        self.song_distances = defaultdict(lambda: defaultdict(lambda: None))
        self.averages = dict()
        self.covariances = dict()
        for song_file in self.song_files:
            song, sr = librosa.load(os.path.join(song_folder, song_file))
            mfcc = librosa.feature.mfcc(song, sr, None, mfcc_amount)
            self.covariances[song_file] = numpy.cov(mfcc)
            self.averages[song_file] = numpy.mean(mfcc, 1)

    def distance(self, song_q, song_p):
        """Calculate the distance between two MFCCs. This is based on this
        paper: http://cs229.stanford.edu/proj2009/RajaniEkkizogloy.pdf
        """

        def kl(p, q):
            cov_p = self.covariances[p]
            cov_q = self.covariances[q]
            cov_q_inv = numpy.linalg.inv(cov_q)
            m_p = self.averages[p]
            m_q = self.averages[q]
            d = cov_p.shape[0]
            return (
                numpy.log(numpy.linalg.det(cov_q) / numpy.linalg.det(cov_p)) +
                numpy.trace(numpy.dot(cov_q_inv, cov_p)) + numpy.dot(
                    numpy.transpose(m_p - m_q), numpy.dot(cov_q_inv,
                                                          (m_p - m_q))) - d
            ) / 2

        return (kl(song_q, song_p) + kl(song_p, song_q)) / 2

    def get_next_song(self, user_feedback):
        """Get the next song by calculcating the distance between this and all
        the other songs and using NCA to pick a song. Based on this paper:
        http://www.cs.cornell.edu/~kilian/papers/Slaney2008-MusicSimilarityMetricsISMIR.pdf
        """
        if self.current_song is None:
            next_song = random.choice(self.song_files)
        else:
            distance_sum = 0
            for song_file in self.song_files:
                # calc distance between song_file and current_song
                if song_file != self.current_song:
                    dst = self.song_distances[self.current_song][song_file]
                    if dst is None:
                        dst = self.distance(self.current_song, song_file)
                        self.song_distances[self.current_song][song_file] = dst
                        self.song_distances[song_file][self.current_song] = dst
                    # calculcate sum of e to the power of -distance for each
                    # distance
                    distance_sum += numpy.power(numpy.e, -dst)
            for song_file in self.song_files:
                # pick file with chance of e to the power of -distance divided
                # by
                # distance_sum
                if song_file == self.current_song:
                    chance = 1 / (1 + self.streak * self.multiplier)
                else:
                    dist = self.song_distances[self.current_song][song_file]
                    chance = numpy.power(
                        numpy.e, -dist) / distance_sum
                if random.random() < chance:
                    break
            next_song = song_file
        if self.current_song == next_song:
            self.streak += 1
        elif self.current_song is not None:
            self.song_files.remove(self.current_song)
        self.current_song = next_song
        return SongStruct(next_song, 0, None)
