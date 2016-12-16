import librosa
import numpy as np


class Song:
    def __init__(self, file_location):
        self.file_location = file_location
        self.curr_time = 0
        self.time_series = self.sampling_rate = None
        self.tempo = self.beat_track = None
        self.set_process_data()

    def set_process_data(self):
        # Load the sample from the given location
        self.time_series, self.sampling_rate = librosa.load(self.file_location)
        # Get the beat track and BPM
        self.tempo, beat_track_frames = librosa.beat.beat_track(
            self.time_series, self.sampling_rate)
        self.beat_track = librosa.core.frames_to_samples(beat_track_frames)

    def next_segment(self, segment_size, begin=False, piemels=False):
        if begin:
            time_vector = np.array([0, 30])
        else:
            time_vector = np.array(
                [self.curr_time, segment_size + self.curr_time])
            self.curr_time += segment_size

        start, end = librosa.core.time_to_samples(time_vector,
                                                  self.sampling_rate)
        return (start, end)

    def time_delta(self, start_frame, end_frame):
        d1, d2 = librosa.samples_to_time(
            np.array([start_frame, end_frame]), self.sampling_rate)
        return d2 - d1

    def frame_to_segment_time(self, segment_size, prev_time, start_frame):
        time_diff = segment_size - prev_time
        d1, d2 = librosa.time_to_samples(
            np.array([0, time_diff]), self.sampling_rate)
        return start_frame + (d2 - d1)

    def beat_track_in_segment(self, seg_start, seg_end):
        beat_tracks = []
        for bt in self.beat_track:
            if bt >= seg_start and bt <= seg_end:
                beat_tracks.append(bt)

        return beat_tracks
