# -*- coding: utf-8 -*-

from .helpers import SongStruct
from collections import defaultdict
import os
import random
import librosa
import numpy
from sklearn.decomposition import PCA


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
    def __init__(self,
                 song_folder,
                 mfcc_amount=20,
                 current_multiplier=0.5,
                 weight_amount=3,
                 cache_dir=None,
                 default_weights=None):
        self.current_song = None
        self.multiplier = current_multiplier
        self.streak = 0
        self.weight_amount = weight_amount
        if default_weights is None:
            self.weigts = [1 / weight_amount for _ in range(weight_amount)]
        else:
            self.weigts = default_weights

        self.song_folder = song_folder
        self.song_files = [f for _, __, f in os.walk(song_folder)][0]
        self.cache_dir = cache_dir
        self.reset_songs()

    def reset_songs(self):
        """Restart with the full amount of songs. This does not alter the
        amount of weights. CAUTION: this call might be slow!"""
        self.song_distances = defaultdict(lambda: defaultdict(lambda: None))
        self.song_properties = dict()
        for song_file in self.song_files:
            filename, _ = os.path.splitext(song_file)
            if self.cache_dir and os.path.exists(
                    os.path.join(self.cache_dir, filename) + os.extsep +
                    'npy'):
                mfcc = numpy.load(
                    os.path.join(self.cache_dir, filename) + os.extsep + 'npy')
            else:
                mfcc = self.get_mfcc(
                    os.path.join(song_folder, song_file), mfcc_amount)
                if self.cache_dir:
                    numpy.save(os.path.join(cache_dir, filename), mfcc)
            covariance = numpy.cov(mfcc)
            pca = PCA(self.weight_amount)
            pca.fit(mfcc.T)
            props = (numpy.linalg.cholesky(covariance), numpy.mean(mfcc, 1),
                     pca.components_.T)

            self.song_properties[song_file] = props

    @staticmethod
    def get_mfcc(song_file, mfcc_amount):
        song, sr = librosa.load(song_file)
        return librosa.feature.mfcc(song, sr, None, mfcc_amount)

    def get_w_matrix(self, pca):
        return numpy.array([
            sum([elem * self.weigts[i] for i, elem in enumerate(row)])
            for row in pca
        ])

    def covariance(self, song_file):
        cholsky, _, pca = self.song_properties[song_file]
        d = numpy.dot(numpy.diag(self.get_w_matrix(pca)), cholsky)
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
        """Get the next song by calculcating the distance between this and all
        the other songs and using NCA to pick a song. Based on this paper:
        http://www.cs.cornell.edu/~kilian/papers/Slaney2008-MusicSimilarityMetricsISMIR.pdf
        """

        max_dst = 0
        dsts = []
        if not self.song_files:
            self.reset_songs()
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
                    max_dst = max(max_dst, dst)
                    dsts.append(dst)
            factor = 100 / max(max_dst, 1)
            print('max:', max_dst)
            for dst in dsts:
                distance_sum += numpy.power(numpy.e, -(dst * factor))
            for song_file in self.song_files:
                # pick file with chance of e to the power of -distance divided
                # by distance_sum
                if song_file == self.current_song:
                    chance = 1 / (1 + self.streak * self.multiplier)
                else:
                    dst = self.song_distances[self.current_song][song_file]
                    print(self.current_song, song_file, dst * factor, " ",
                          factor, " ", distance_sum)
                    chance = numpy.power(numpy.e,
                                         -(dst * factor)) / distance_sum
                print(self.current_song, song_file, chance)
                if random.random() < chance:
                    print('picked')
                    break
            next_song = song_file
        if self.current_song == next_song:
            self.streak += 1
        elif self.current_song is not None:
            self.song_files.remove(self.current_song)
            self.streak = 0
        self.current_song = next_song
        random.shuffle(self.song_files)
        return SongStruct(next_song, 0, None)
