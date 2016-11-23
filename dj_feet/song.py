import librosa
import numpy as np


class Song:
    def __init__(self, file_location, curr_frame):
        self.file_location = file_location
        self.curr_time = 0
        # Load the sample from the given location
        self.time_series, self.sampling_rate = librosa.load(file_location, sr=32000)
        # Get the beat track and BPM
        self.tempo, self.beat_track = librosa.beat.beat_track(self.time_series,
                                                              self.sampling_rate)
        print(self.file_location, self.sampling_rate)

    def next_segment(self, segment_size, begin=False):
        if begin:
            time_vector = np.array([0, segment_size])
        else:
            time_vector = np.array([self.curr_time,
                                   segment_size + self.curr_time])
            self.curr_time += segment_size

        start, end = librosa.core.time_to_samples(time_vector,
                                                 self.sampling_rate)
        return (start, end)

    def time_delta(self, start_frame, end_frame):
        d1, d2 = librosa.samples_to_time(np.array([start_frame, end_frame]),
                                        self.sampling_rate)
        return d2 - d1

    def frame_to_segment_time(self, segment_size, prev_time, start_frame):
        time_diff = segment_size - prev_time
        d1, d2 = librosa.time_to_samples(np.array([0, time_diff]),
                                             self.sampling_rate)
        return start_frame + (d2 - d1)
