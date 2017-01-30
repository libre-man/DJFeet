"""This file contains the classes needed to represent a song"""
import librosa
import numpy as np


class Song:
    """A song with the needed data for the merger."""
    def __init__(self, file_location, process=True):
        self.file_location = file_location
        self.curr_time = 0
        self.time_series = self.sampling_rate = None
        self.tempo = self.beat_track = None
        if process:
            self.set_process_data()

    def set_process_data(self):
        """Process data and set the class fields. This takes a long time!"""
        # Load the sample from the given location
        self.time_series, self.sampling_rate = librosa.load(self.file_location)
        # Get the beat track and BPM
        self.tempo, beat_track_frames = librosa.beat.beat_track(
            self.time_series, self.sampling_rate)
        self.beat_track = librosa.core.frames_to_samples(beat_track_frames)

    def next_segment(self, segment_size, begin=False):
        """Get the next sector starting from the `begin` or `curr_time` of
        `segment_size` long."""
        if begin:
            time_vector = np.array([0, segment_size])
        else:
            time_vector = np.array(
                [self.curr_time, segment_size + self.curr_time])

        start, end = librosa.core.time_to_samples(time_vector,
                                                  self.sampling_rate)
        return (start, end)

    def time_delta(self, start_frame, end_frame):
        """Give the time delta between two given frames."""
        d1, d2 = librosa.samples_to_time(
            np.array([start_frame, end_frame]), self.sampling_rate)
        return d2 - d1

    def frame_to_segment_time(self, segment_size, start_frame):
        """Give a frame `segement_size` amount of seconds away from the given
        start_frame"""
        time_diff = segment_size
        d1, d2 = librosa.time_to_samples(
            np.array([0, time_diff]), self.sampling_rate)
        return start_frame + (d2 - d1)

    def beat_tracks_in_segment(self, seg_start, seg_end):
        """Get all beats between the `seg_start` and the `seg_end` frames.."""
        beat_tracks = []
        for bt in self.beat_track:
            if bt >= seg_start and bt <= seg_end:
                beat_tracks.append(bt)

        return beat_tracks

    def segment_size_left(self, segment_size):
        """
        Returns true if there's more or equal to segment_size time left in the
        song starting from curr_time, false if not.
        """
        curr_sample = librosa.core.time_to_samples(np.array(self.curr_time),
                                                   self.sampling_rate)
        return self.time_delta(curr_sample,
                               len(self.time_series) - 1) >= segment_size
