# -*- coding: utf-8 -*-

from .helpers import EPSILON
from .song import Song
from collections import defaultdict
import os
import random
import librosa
import numpy
from sklearn.decomposition import PCA
from copy import copy


class Picker:
    def __init__(self):
        pass

    def get_next_song(self, user_feedback):
        """Return a Song for the next song that should be used"""
        raise NotImplementedError("This should be overridden")


class SimplePicker(Picker):
    def __init__(self, song_folder):
        super(SimplePicker, self).__init__()
        self.song_files = [
            os.path.join(song_folder, f) for f in os.listdir(song_folder)
            if os.path.isfile(os.path.join(song_folder, f))
        ]

    def get_next_song(self, user_feedback):
        next_song = ""
        while not os.path.isfile(next_song):
            if not self.song_files:
                raise ValueError("There are no songs left")
            next_song = random.choice(self.song_files)
            self.song_files.remove(next_song)
        return Song(next_song)


class NCAPicker(Picker):
    def __init__(self,
                 song_folder,
                 mfcc_amount=20,
                 current_multiplier=0.5,
                 weight_amount=4,
                 cache_dir=None,
                 weights=None):
        super(NCAPicker, self).__init__()

        self.weight_amount = weight_amount
        # Weights will be set in calculate_song_characteristics if
        # self.weights are None.
        self.weights = weights
        if weights is not None:
            if abs(sum(self.weights) - 1) > EPSILON or len(
                    self.weights) != weight_amount:
                raise ValueError(
                    "The amount of weights should be equal to `weight_amount`"
                    " and sum to 1")

        if mfcc_amount < weight_amount:
            raise ValueError("You cannot have more weights than mfcc vectors")

        self.song_distances = defaultdict(lambda: defaultdict(lambda: None))
        self.song_properties = dict()
        self._song_files = [
            os.path.join(song_folder, f) for f in os.listdir(song_folder)
            if os.path.isfile(os.path.join(song_folder, f))
        ]
        self.song_files = copy(self._song_files)

        characteristics = self.calculate_songs_characteristics(mfcc_amount,
                                                               cache_dir)
        self.pca, self.song_properties, self.weights = characteristics

        self.song_distances = defaultdict(lambda: defaultdict(lambda: None))
        self.current_song = None
        self.multiplier = current_multiplier
        self.streak = 0

    def calculate_songs_characteristics(self, mfcc_amount, cache_dir):
        """Calculate the songs characteristics. These are returned as a tuple
        of the PCA and dictionary for in which each song has a tuple of their
        cholesky decomposition and the mean of their mfcc.
        """
        mfccs = dict()
        average = numpy.zeros(mfcc_amount)
        song_properties = dict()

        # Calculate the average 20D feature vector for the mfccs
        for song_file in self.song_files:
            filename, _ = os.path.splitext(os.path.basename(song_file))
            if cache_dir and os.path.isfile(
                    os.path.join(cache_dir, filename) + os.extsep + 'npy'):
                mfcc = numpy.load(
                    os.path.join(cache_dir, filename) + os.extsep + 'npy')
            else:
                mfcc = self.get_mfcc(song_file, mfcc_amount)
                if cache_dir:
                    numpy.save(os.path.join(cache_dir, filename), mfcc)
            mfccs[song_file] = mfcc
            average += mfcc.mean(1)

        # NOTE: We don't use the length of the songs as weights. Because we
        # prefer to weigh each song equally. This is also influenced by the
        # fact that we don't know how long each song will be played so using
        # the entire length doesn't really make any sense.
        average = average / len(self.song_files)
        average_covariance = numpy.array(
            [numpy.zeros(mfcc_amount) for _ in range(mfcc_amount)])

        # Now calculate the centered mfcc and covariance matrix for each song
        # and keep a running average of the average covariance matrix.
        for song_file, mfcc in mfccs.items():
            mfcc = (mfcc.T - average).T
            covariance = numpy.cov(mfcc)
            average_covariance += covariance
            props = (numpy.linalg.cholesky(covariance), numpy.mean(mfcc, 1))
            song_properties[song_file] = props

        # Do PCA on the average covariance matrix
        average_covariance = average_covariance / len(self.song_files)
        pca = PCA(self.weight_amount)
        pca.fit(average_covariance.T)

        # Initialize the weights to the explained variance ratio if the weights
        # are not yet set.
        if self.weights is None:
            weights = pca.explained_variance_ratio_
        else:
            weights = self.weights

        return pca.components_.T, song_properties, weights

    def reset_songs(self):
        """Restart with the full amount of songs. This does not alter the
        weights."""
        self.song_files = copy(self._song_files)

    @staticmethod
    def get_mfcc(song_file, mfcc_amount):
        """Calculate the mfcc for the given song."""
        song, sr = librosa.load(song_file)
        return librosa.feature.mfcc(song, sr, None, mfcc_amount)

    def get_w_vector(self, pca):
        """Get a weighted pca matrix"""
        return numpy.array([
            sum((elem * self.weights[i] for i, elem in enumerate(row)))
            for row in pca
        ])

    def covariance(self, song_file):  #
        """Calculate a (approximation) of the covariance matrix using PCA and a
        cholesky decomposition."""
        cholesky, _ = self.song_properties[song_file]
        d = numpy.dot(numpy.diag(self.get_w_vector(self.pca)), cholesky)
        return numpy.dot(d, d.T)

    def distance(self, song_q, song_p):
        """Calculate the distance between two MFCCs. This is based on this
        paper: http://cs229.stanford.edu/proj2009/RajaniEkkizogloy.pdf
        """

        def kl(p, q):
            cov_p = self.covariance(p)
            cov_q = self.covariance(q)
            cov_q_inv = numpy.linalg.inv(cov_q)
            m_p = self.song_properties[p][1]
            m_q = self.song_properties[q][1]
            d = cov_p.shape[0]
            return (
                numpy.log(numpy.linalg.det(cov_q) / numpy.linalg.det(cov_p)) +
                numpy.trace(numpy.dot(cov_q_inv, cov_p)) + numpy.dot(
                    numpy.transpose(m_p - m_q),
                    numpy.dot(cov_q_inv, (m_p - m_q))) - d) / 2

        return (kl(song_q, song_p) + kl(song_p, song_q)) / 2

    def get_next_song(self, user_feedback):
        """Get the next song to play. Do this by random for the first and
        otherwise use `_find_next_song`"""
        # We have only one song remaining so we won't be able to pick good new
        # songs. So reset all the available songs.
        if len(self.song_files) == 1:
            self.reset_songs()

        if self.current_song is None:  # First pick, simply select random
            next_song = random.choice(self.song_files)
        else:
            next_song = self._find_next_song()

        if self.current_song == next_song:  # Kept same song
            self.streak += 1
        elif self.current_song is not None:
            # Remove the old song from the available so we have fresh tunes
            self.song_files.remove(self.current_song)
            self.streak = 0

        self.current_song = next_song
        return Song(next_song)

    def _find_next_song(self):
        """Find the next song by getting the distance between the current and
        the potential song, doing softmax with these distances and getting one
        by chance. Based on this paper:
        http://www.cs.cornell.edu/~kilian/papers/Slaney2008-MusicSimilarityMetricsISMIR.pdf
        """
        # TODO: discard songs with a wrong tempo!
        max_dst = 0
        for song_file in self.all_but_current_song():
            # calc distance between song_file and current_song
            dst = self.song_distances[self.current_song][song_file]
            if dst is None:
                dst = self.distance(self.current_song, song_file)
                self.song_distances[self.current_song][song_file] = dst
                self.song_distances[song_file][self.current_song] = dst

            max_dst = max(max_dst, dst)

        # Find the max distance and normalize it to 50. This is because of
        # floating point errors when doing something to the power of a very
        # large negative number
        factor = 50 / max(max_dst, 1)

        # Now calculate the distance sum needed for softmax
        distance_sum = 0
        for song_file in self.all_but_current_song():
            dst = self.song_distances[self.current_song][song_file]
            distance_sum += numpy.power(numpy.e, -(dst * factor))

        chances = []
        for song_file in self.song_files:
            # Append the softmax chances to the chances list
            if song_file != self.current_song:
                dst = self.song_distances[self.current_song][song_file]
                chance = numpy.power(numpy.e, -(dst * factor)) / distance_sum
                chances.append((song_file, chance))

        # Square the chances and then normalize them again. This has the
        # advantage of giving relative high chances, so similar songs, a
        # relative higher chance will still remaining a vector sum of 1.
        for i in range(len(chances)):
            chances[i] = (chances[i][0], chances[i][1]**2)
        chance_sum = sum((x[1] for x in chances))
        for i in range(len(chances)):
            chances[i] = (chances[i][0], chances[i][1] / chance_sum)

        chances.append(
            (self.current_song, 1 / (1 + self.streak * self.multiplier)))

        # Sort the chances by descending chance
        chances.sort(key=lambda x: x[1])

        # We do a range 10 so we are almost certain we find a match within the
        # loop however we won't crash or slowdown to much if this doesn't
        # happen.
        next_song = chances[0]
        for _ in range(10):
            for song_file, chance in chances:
                if random.random() < chance:
                    next_song = song_file
                    break
        return next_song

    def all_but_current_song(self):
        """A generator that yields all but the current song of all played
        songs."""
        for song_file in self.song_files:
            if song_file != self.current_song:
                yield song_file
