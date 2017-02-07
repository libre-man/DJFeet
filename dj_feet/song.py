"""This file contains the classes needed to represent a song"""
import librosa
import numpy as np


class Song:
    """A Song object containing a song with a specific state.

    This object can load in a song from a given location using librosa. It will
    in addition hold the song's beat track and basic characteristics. Multiple
    operations on the song can be done. In addition, this class contains
    multiple functions to convert different time units.
    """
    def __init__(self, file_location, process=True):
        """
        :param string file_location: The path to the wav file to use as base
                                     for this song.
        :param bool process: Indicate if we should process the song in the
                             ``__init__`` method. This may be really slow, but
                             methods may not work without doing this.
        """
        self.file_location = file_location
        self.curr_time = 0
        self.time_series = self.sampling_rate = None
        self.tempo = self.beat_track = None
        if process:
            self.set_process_data()

    def set_process_data(self):
        """Process / load data and set the class fields.

        Load the song using librosa and find the beat track to set class fields
        for future use. Please note that this operation may take a long time!

        :returns: Always returns None
        :rtype: None
        """
        # Load the sample from the given location
        self.time_series, self.sampling_rate = librosa.load(self.file_location)
        # Get the beat track and BPM
        self.tempo, beat_track_frames = librosa.beat.beat_track(
            self.time_series, self.sampling_rate)
        self.beat_track = librosa.core.frames_to_samples(beat_track_frames)

    def next_segment(self, segment_size, begin=False):
        """Get the next sector starting from the ``begin`` or ``curr_time`` of
        ``segment_size`` long.

        Get the next sector (a part of the song of given ``segment_size`` long)
        of the song if ``begin`` is False. Get the first ``segment_size`` of
        the song otherwise.

        :param int segment_size: The length of the next sector to get in
                                 seconds.
        :param bool begin: Whether the sector should be gotten from the song's
                           current time or from the beginning of the song.
        :returns: A tuple with the sample index of respectively the first and
                  last sample of the next sector.
        :rtype: tuple(int, int)
        """
        if begin:
            time_vector = np.array([0, segment_size])
        else:
            time_vector = np.array(
                [self.curr_time, segment_size + self.curr_time])

        start, end = librosa.core.time_to_samples(time_vector,
                                                  self.sampling_rate)
        return (start, end)

    def time_delta(self, start_frame, end_frame):
        """Find the time delta between two given sample indices.

        Find the time delta (in seconds) between two given sample indices. That
        is the difference in time (seconds) between the given sample indices.

        :param int start_frame: The index of the first sample.
        :param int end_frame: The index of the last sample.
        :returns: The difference in seconds between both given samples.
        :rtype: int
        """
        d1, d2 = librosa.samples_to_time(
            np.array([start_frame, end_frame]), self.sampling_rate)
        return d2 - d1

    def frame_to_segment_time(self, segment_size, start_frame):
        """Give a sample ``segement_size`` amount of seconds away from the given
        ``start_frame``.

        Find the index of a sample that is exactly ``segment_size`` seconds
        after the given ``start_frame``. No guarantees are made that this given
        sample index is a valid index for the given song, this should be
        checked manually.

        :param int segment_size: The time in seconds between the given
                             ``start_frame`` and the returned sample index.
        :param int start_frame: The index of the sample to find the sample
                            ``segment_size`` seconds away from.
        :returns: A sample index that is ``segment_size`` seconds after the
                  given ``start_frame``.
        :rtype: int
        """
        time_diff = segment_size
        d1, d2 = librosa.time_to_samples(
            np.array([0, time_diff]), self.sampling_rate)
        return start_frame + (d2 - d1)

    def beat_tracks_in_segment(self, seg_start, seg_end):
        """Get all beats between the ``seg_start`` and the ``seg_end`` frames.

        Given two sample indices ``seg_start`` and ``seg_end`` find all current
        song's beats that are in between this range (inclusive).

        :param int seg_start: The sample index indicating the beginning of the
                              range to find beats on.
        :param int seg_end: The sample index indicating the end of the range to
                            find beats on.
        :returns: A list containing all indices of beats in the given range.
        :rtype: numpy.array(int)
        """
        beat_tracks = []
        for bt in self.beat_track:
            if bt >= seg_start and bt <= seg_end:
                beat_tracks.append(bt)

        return beat_tracks

    def segment_size_left(self, segment_size):
        """
        Returns true if there's more or equal to ``segment_size`` time left in
        the song starting from ``curr_time``, false if not.

        Finds whether another segment of ``segment_size`` seconds long is
        available in the song or that the song is too close to it's end. It is
        assumed that the song's current position is correctly stored in
        the ``cur_time`` variable (which it should).

        :param int segment_size: The length in seconds of a segment.
        :returns: True if the song's current position is more than
                  ``segment_size`` seconds from the end. False otherwise.
        :rtype: boolean
        """
        curr_sample = librosa.core.time_to_samples(np.array(self.curr_time),
                                                   self.sampling_rate)
        return self.time_delta(curr_sample,
                               len(self.time_series) - 1) >= segment_size
