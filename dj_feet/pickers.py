# -*- coding: utf-8 -*-

from .helpers import EPSILON
from .song import Song
import dj_feet.feedback
from collections import defaultdict
import os
import random
import librosa
import numpy
from sklearn.decomposition import PCA
from copy import copy
import scipy
import logging

l = logging.getLogger(__name__)


class Picker:
    """This is the base Picker class.

    You should not use this class directly but should inherit from this class
    if you want to implement a new picker. A subclass should override all
    public methods of this class.
    """

    def get_next_song(self, user_feedback, force=False):
        """Get the next song that should be used.

        .. note:: This function has to build in safeties to protect it from not
                  returning something useful after several calls with ``force``
                  set to ``True``.

        .. warning:: The ``user_feedback`` argument is not the feedback of the
                     previous song but that of some iterations back. For more
                     information of the timeline see how the :class:`NCAPicker`
                     handles this and see :ref:`the timeline.<djfeet-timeline>`

        :param dict user_feedback: The user-feedback of the transition
                                   that was done 5 non ``force`` iterations
                                   ago.
        :param bool force: Indicating if we have to change song right now. This
                           means the previous return value of
                           :func:`get_next_song` was not used.
        :rtype: dj_feet.song.Song
        """
        raise NotImplementedError("This should be overridden")

    @staticmethod
    def process_song_file(song_file):
        """Process the given music file.

        If you give this method any variables these need to have the same name
        as in your ``__init__`` method, where they also have to occur! These
        variables will be marked as needs_reload. They can have default values.

        Please note that this is a static methode. Therefore this method can
        and should have side effects as you have no access to the ``self``
        variable.

        :param str song_file: This variable will always be given and should not
                          be a variable in your ``__init__`` method. This is
                          the current file to process. Please note that it is
                          not guaranteed that this song will also be in the
                          final directory to play.
        :returns: This does not matter as it will not be used by the framework.
        """
        raise NotImplementedError("This should be overridden")


class SimplePicker(Picker):
    """A simple picker that chooses songs randomly.

    This picker should not be used if you want any kind of intelligent
    transitioning of songs. This picker will always pick a new random song and
    will never pick the same song twice.
    """

    def __init__(self, song_folder):
        """Initialize the the ``SimplePicker`` object.

        :param str song_folder: The folder that contains the wav files to use.
        """
        super(SimplePicker, self).__init__()
        self.song_files = [
            os.path.join(song_folder, f) for f in os.listdir(song_folder)
            if os.path.isfile(os.path.join(song_folder, f))
        ]

    def get_next_song(self, user_feedback, force=False):
        """Get the next song.

        This next song is always different from the previous song.

        :param dict user_feedback: This is ignored.
        :param bool force: This is also ignored as the returned song is always
                      a new song.
        :returns: A chosen song that has not been chosen yet.
        :rtype: dj_feet.song.Song
        :raises ValueError: If there are no songs left in ``song_files`` that
                            are not yet picked.
        """
        next_song = ""
        while not os.path.isfile(next_song):
            if not self.song_files:
                raise ValueError("There are no songs left")
            next_song = random.choice(self.song_files)
            self.song_files.remove(next_song)
        return Song(next_song)

    @staticmethod
    def process_song_file(song_file):
        """This does nothing however it is required.

        We don't need to process music, as we are not using any characteristics
        of music.

        :param str song_file: The path to the wav to be processed.
        :rtype: None
        """
        return None


class NCAPicker(Picker):
    """This an sophisticated picker based on weighted NCA using user feedback.

    This picker calculates the MFCC of every song. Using this MFCC it
    calculates a covariance matrix. This covariance matrix and the PCA of the
    average covariance matrix is used to calculate the Kullback-Liebler
    divergence which is used as distance metric between the songs. These songs
    are first pruned based on tempo. This distance is then softmaxed and the
    chances are simulated.

    The feedback is to optimize a weight vector using ``scipy.optimize``. This
    means that over time the distances should start to reflect how much the
    dancers like the music instead of just the similarity between the songs.

    This picker also contains checks and safeguards for not getting stuck in an
    infinite loop and will reuse songs if no suitable new songs can be found.
    It can also self loop, which is done with a chance that decreases
    asymptotic.
    """

    def __init__(self,
                 song_folder,
                 mfcc_amount=20,
                 current_multiplier=0.3,
                 weight_amount=4,
                 cache_dir=None,
                 weights=None,
                 feedback_method='default',
                 max_tempo_percent=None,
                 max_force_streak=10):
        """Create a new NCAPicker instance.

        :param str song_folder: The folder of the wav file to use for merging.
        :param int mfcc_amount: The number of mfcc's to use for picking.
        :param float current_multiplier: The amount to reduce the chance that
                                         we will self loop. This is done by the
                                         following formula: 1 / (1 + streak *
                                         multiplier). This means that lower
                                         means more self loops. If this
                                         variable is too low there will be too
                                         many self loops and the picker might
                                         not actually use its NCA qualities to
                                         ever chose a new song so beware.
        :param int weight_amount: The amount of weights to use, a value of
                                  around 4 is good. It should be less then
                                  mfcc_amount.
        :param str cache_dir: The directory to use for caching purposes.
        :param weights: The default weights to use. If this is a list it should
                        have a length of ``weight_amount``
        :type weights: None or list(float)
        :param str feedback_method: The method to use for getting feedback.
        :param int max_tempo_percent: The maximum percentage the tempo of a new
                                      song can differ from the tempo of the
                                      current song.
        :param int max_force_streak: The maximum number of successive calls to
                                     ``get_next_song`` before we should reset
                                     all the songs to start using already used
                                     songs.
        """
        super(NCAPicker, self).__init__()

        self.weight_amount = weight_amount
        # Weights will be set in calculate_song_characteristics if
        # self.weights are None.
        self.weights = weights
        if weights is not None:
            if abs(sum(self.weights) - 1) > EPSILON or len(
                    self.weights) != weight_amount:
                raise ValueError("The amount of weights should be equal to" +
                                 " ``weight_amount`` and sum to 1")

        if mfcc_amount < weight_amount:
            raise ValueError("You cannot have more weights than mfcc vectors")

        self.get_feedback = getattr(dj_feet.feedback,
                                    "feedback_" + feedback_method)
        self.picked_songs = list()
        self.done_transitions = list()

        self.song_distances = defaultdict(lambda: defaultdict(lambda: None))
        self.song_properties = dict()
        self._song_files = [
            os.path.join(song_folder, f) for f in os.listdir(song_folder)
            if os.path.isfile(os.path.join(song_folder, f))
        ]
        self.song_files = copy(self._song_files)

        if max_tempo_percent is None:
            max_tempo_percent = 8
        self.max_tempo_percent = int(max_tempo_percent)

        characteristics = self.calculate_songs_characteristics(mfcc_amount,
                                                               cache_dir)
        self.pca, self.song_properties, self.weights = characteristics

        self.song_distances = defaultdict(lambda: defaultdict(lambda: None))
        self.current_song = None
        self.multiplier = current_multiplier
        self.streak = 0
        self.force_streak = 0
        self.max_force_streak = max_force_streak

    @staticmethod
    def process_song_file(mfcc_amount, cache_dir, song_file):
        """Process the given ``song_file``.

        This is done by calculating its ``mfcc`` and its tempo and storing this
        information in the given cache_dir.

        :param str song_file: The wav file of the song to process.
        :param int mfcc_amount: The amount of mfcc's to calculate.
        :param str cache_dir: The directory to save the cached properties in.
        :return: A tuple of the mfcc and tempo in this order.
        :rtype: tuple
        """
        l.info("Loading MFCC and tempo variables from %s.", song_file)
        mfcc, tempo = NCAPicker.get_mfcc_and_tempo(song_file, mfcc_amount)
        l.debug("Loaded mfcc and tempo. Writing mfcc.")

        filename, _ = os.path.splitext(os.path.basename(song_file))
        cache_file = os.path.join(cache_dir, filename)
        numpy.save(cache_file + "_mfcc", mfcc)
        l.debug("Done writing mfcc, writing tempo.")
        numpy.save(cache_file + "_tempo", tempo)
        l.debug("Done writing tempo. Touching done file.")
        with open(cache_file + "_done", "w+"):
            pass
        l.info("Done with processing %s.", song_file)

        return mfcc, tempo

    def calculate_songs_characteristics(self, mfcc_amount, cache_dir):
        """Calculate the songs characteristics.

        :param int mfcc_amount: The amount of mfccs to calculate.
        :param cache_dir: The directory to find and store the cache. The bpm
                          and mfcc is cached. If it is False caching is
                          disabled.
        :type cache_dir: str or ``False``
        :returns: A tuple of respectively their PCA components, a dictionary
                  for in which each song has a tuple of respectively their
                  cholesky decomposition, the mean of their mfcc and their
                  average BPM. Finally the return tuple contains the current
                  weights for calculating the covariance matrix.
        :rtype: tuple(numpy.array,
                      dict[string, tuple(numpy.array, int, int)],
                      numpy.array)
        """
        mfccs = dict()
        tempos = dict()
        average = numpy.zeros(mfcc_amount)
        song_properties = dict()

        # Calculate the average 20D feature vector for the mfccs
        for song_file in self.song_files:
            filename, _ = os.path.splitext(os.path.basename(song_file))
            l.debug("Currently loading %s.", filename)
            if cache_dir and os.path.isfile(
                    os.path.join(cache_dir, filename + "_done")):
                l.debug("Loading our song from cache.")
                mfcc = numpy.load(
                    os.path.join(cache_dir, filename + "_mfcc") + os.extsep +
                    'npy')
                tempo = numpy.load(
                    os.path.join(cache_dir, filename + "_tempo") + os.extsep +
                    'npy')
            else:
                l.debug("Song not found in cache, processing it.")
                if cache_dir:
                    mfcc, tempo = self.process_song_file(mfcc_amount,
                                                         cache_dir, song_file)
                else:
                    mfcc, tempo = self.get_mfcc_and_tempo(song_file,
                                                          mfcc_amount)

            mfccs[song_file] = mfcc
            tempos[song_file] = tempo
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
            props = (numpy.linalg.cholesky(covariance), numpy.mean(mfcc, 1),
                     tempos[song_file])
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
        """Reset ``self.song_files`` to its original value.

        This does not alter the weights calculated till now.

        :rtype: None
        """
        l.debug("Resetting songs.")
        self.song_files = copy(self._song_files)

    @staticmethod
    def get_mfcc_and_tempo(song_file, mfcc_amount):
        """Calculate the mfcc and estimated BPM.

        :param str song_file: This file to calculate for.
        :param int mfcc_amount: The amount of mfccs to calculate.
        :returns: A tuple of the mfccs and tempo in BPM in this order.
        :rtype: tuple
        """
        song, sr = librosa.load(song_file)
        tempo, _ = librosa.beat.beat_track(song, sr)
        return librosa.feature.mfcc(song, sr, None, mfcc_amount), tempo

    @staticmethod
    def get_w_vector(pca, weights):
        """Get a weighted pca matrix.

        :param numpy.array(numpy.array) pca: The PCA to apply the weights on.
        :param numpy.array(len(pca)) weights: The weights to apply.
        :returns: A square matrix of the same size as the PCA.
        :rtype: numpy.array
        """
        return numpy.array([
            sum((elem * weights[i] for i, elem in enumerate(row)))
            for row in pca
        ])

    def covariance(self, song_file, weights):
        """Calculate a (approximation) of the covariance matrix.

        This is done by using a PCA and a cholesky decomposition.

        :param str song_file: The path to the song that should be used. Please
                          note that this path should be in
                          ``self.song_properties``.
        :param numpy.array weights: The weights to be used.
        :returns: A square matrix of the same size as the weights vector.
        :rtype: numpy.array
        """
        cholesky, _, _unused = self.song_properties[song_file]
        d = numpy.dot(
            numpy.diag(self.get_w_vector(self.pca, weights)), cholesky)
        return numpy.dot(d, d.T)

    def distance(self, song_q, song_p, weights=None):
        """Calculate the distance between two MFCCs.

        This is done based on this paper:
        http://cs229.stanford.edu/proj2009/RajaniEkkizogloy.pdf

        :param str song_q: The first song used.
        :param str song_p: The second song used.
        :param numpy.array weights: The weights vector to use.
        :returns: The distance between the two given songs. This distance is
                  symmetric.
        :rtype: int
        """
        if weights is None:
            weights = self.weights

        def kl(p, q):
            cov_p = self.covariance(p, weights)
            cov_q = self.covariance(q, weights)
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

    def get_next_song(self, user_feedback, force=False):
        """Get the next song to play.

        Do this randomly for the first and otherwise use
        :func:`_find_next_song`. This also calls :func:`_optimize_weights` if
        we got useful feedback (based on the current song we are mixing). If
        ``get_next_song`` was ``True`` too many times we pick random again.

        :param dict user_feedback: The user feedback between the song of five
                                   and four picks ago.
        :param bool force: Indicate that the previous pick was not expectable.
        :return: The song to play next:
        :rtype: Song
        """
        # We have only one song remaining so we won't be able to pick good new
        # songs. So reset all the available songs.
        if len(self.song_files) == 1:
            self.reset_songs()
        if (not force) and len(self.picked_songs) == 5:
            old = self.picked_songs.pop(0)
            if old != self.picked_songs[-4]:
                new = self.picked_songs[-4]
                l.debug("Trying to interpreted user feedback from %s to %s.",
                        old, new)
                user_feedback.update({"old": old, "new": new})
                self.done_transitions.append(
                    (old, new, self.get_feedback(user_feedback)))
                self._optimize_weights()

        if force:
            self.force_streak += 1
        else:
            self.force_streak = 0

        if self.force_streak > self.max_force_streak:
            self.reset_songs()

        if self.current_song is None:  # First pick, simply select random
            next_song = random.choice(self.song_files)
        else:
            next_song = self._find_next_song(force)

        if force:
            self.picked_songs[-1] = next_song
        else:
            self.picked_songs.append(next_song)

        if (not force) and self.current_song == next_song:  # Kept same song
            self.streak += 1
        elif self.current_song is not None:
            # Remove the old song from the available so we have fresh tunes
            self.song_files.remove(self.current_song)
            self.streak = 0

        self.current_song = next_song
        return Song(next_song)

    def _find_next_song(self, force):
        """Find the next song by doing song analysis.

        This gets the distance between the current and the potential song,
        does softmax with these distances and gets one by chance. Based on this
        paper:
        http://www.cs.cornell.edu/~kilian/papers/Slaney2008-MusicSimilarityMetricsISMIR.pdf

        :param bool force: Make it impossible to pick the current song.
        :returns: The filename of the next song.
        :rtype: str
        """
        l.debug("Finding song by using NCA.")

        max_dst = 0
        filter_songs = self.force_streak < 2
        for song_file in self.all_but_current_song(filter_songs=filter_songs):
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
        for song_file in self.all_but_current_song(filter_songs=filter_songs):
            dst = self.song_distances[self.current_song][song_file]
            distance_sum += numpy.power(numpy.e, -(dst * factor))

        chances = []
        for song_file in self.all_but_current_song(filter_songs=filter_songs):
            # Append the softmax chances to the chances list
            if song_file != self.current_song:
                dst = self.song_distances[self.current_song][song_file]
                chance = numpy.power(numpy.e, -(dst * factor)) / distance_sum
                chances.append((song_file, chance))

        chances = list(
            zip([x for x, _ in chances],
                self.normalize_chances([x for _, x in chances])))

        if not force:
            chances.append(
                (self.current_song, 1 / (1 + self.streak * self.multiplier)))

        if not chances:
            self.reset_songs()
            self.force_streak += 1
            return self._find_next_song(force)

        # Sort the chances by descending chance
        chances.sort(key=lambda x: x[1])

        # We do a range 10 so we are almost certain we find a match within the
        # loop however we won't crash or slowdown to much if this doesn't
        # happen.
        next_song = chances[0][0]
        for _ in range(10):
            for song_file, chance in chances:
                if random.random() < chance:
                    next_song = song_file
                    l.debug("Found next_song %s, its chance was %f", next_song,
                            chance)
                    break
            else:
                continue
            # Make sure we actually break the OUTER loop
            break
        else:
            l.critical("Terminated simulating odds without finding," +
                       " picking song with highest odds (%s).", next_song)
        return next_song

    @staticmethod
    def normalize_chances(original_chances):
        """Normilize the chances by squaring them and normalizing them again.

        Square the chances and then normalize them again. This has the
        advantage of giving relative high chances (similar songs) a
        higher chance while still remaining a vector sum of 1.

        :param list(int) original_chances: The original chances of the songs.
        :returns: The new chances in the same order the input was.
        :rtype: list(int)
        """
        chances = list()
        for chance in original_chances:
            chances.append(chance**2)
        chance_sum = sum(chances)
        for i in range(len(chances)):
            chances[i] = chances[i] / chance_sum
        return chances

    def _optimize_weights(self):
        """Optimize the weights of the picker.

        This function optimizes the weights based on the saved feedback between
        to songs using the :func:`scipy.optimize.minimize` function. It
        constrains the weights to sum to 1.

        :returns: Nothing of value.
        :rtype: None
        """
        l.debug("Optimize the current weights.")

        def func_to_optimize(weights):
            feedback_dsts = list()
            feedbacks = list()
            chances = list()

            max_dst = -1
            for prev_song, next_song, feedback in self.done_transitions:
                dst = self.distance(prev_song, next_song, weights)
                feedback_dsts.append((feedback, dst))
                max_dst = max(max_dst, dst)
            factor = 50 / float(max_dst)
            distance_sum = sum((dst * factor for _, dst in feedback_dsts))
            for feedback, dst in feedback_dsts:
                chance = numpy.power(numpy.e, -(dst * factor)) / distance_sum
                feedbacks.append(feedback)
                chances.append(chance)
            chances = self.normalize_chances(chances)
            res_diff = 0

            for feedback, chance in zip(feedbacks, chances):
                res_diff = abs(feedback - chance)
            return res_diff

        def contrains_fun(weights):
            diff = sum(weights) - 1
            return diff

        res = scipy.optimize.minimize(
            func_to_optimize,
            tuple(self.weights),
            method='SLSQP',
            constraints={'type': 'eq',
                         'fun': contrains_fun},
            jac=False,
            bounds=[[0, 1] for _ in self.weights])
        if res.success:
            self.weights = res.x

    def all_but_current_song(self, filter_songs=True):
        """Get all songs except for the current song.

        This does not include songs that were played since the last call to
        :func:`reset_songs`.

        :param bool filter_songs: Indicate if the iterator should filter songs
                                  based on tempo.
        :yields: All songs that are not yet played except for the current song.
        :rtype: str
        """
        iterator = self.all_close_songs() if filter_songs else self.song_files
        for song_file in iterator:
            if song_file != self.current_song:
                yield song_file

    def all_close_songs(self, base_song=None):
        """Get all songs filtered by their average tempo.

        This function makes a generator that contains all not played songs
        after the last call to :func:`reset_songs` filtered by their tempo,
        which can have a maximum percentage offset of ``max_tempo_percent``
        given to :class:`NCAPicker`.

        :param string base_song: The base song of which its tempo used for
                                 filtering, if ``None`` the current song is
                                 used.
        :yields: A generator filtered by tempo.
        :rtype: str
        """
        if base_song is None:
            base_song = self.current_song
        _, _unused, base_tempo = self.song_properties[base_song]
        tempo_factor = self.max_tempo_percent / 100
        for song_file in self.song_files:
            _, _unused, other_tempo = self.song_properties[song_file]
            tempo_offset = abs(base_tempo - other_tempo)
            if tempo_factor * other_tempo > tempo_offset:
                yield song_file
            else:
                l.debug("Discarding %s because of its tempo.", song_file)
