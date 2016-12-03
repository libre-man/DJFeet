# -*- coding: utf-8 -*-
import librosa
from pydub import AudioSegment
#from .helpers import SongStruct
from .song import Song
from tempfile import NamedTemporaryFile
import numpy as np

SAMPLING_RATE = 32000

class Transitioner:
    def __init__(self):
        pass

    def merge(self, prev_song, next_song):
        """
        Prev_song and next_song both need to be song objects.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")

    def write_sample(self, sample):
        """Write the given sample to the output stream.
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")


class SimpleTransitioner(Transitioner):
    def __init__(self, output, merge_time=100):
        self.output = output
        self.merge_time = merge_time

    def merge(self, prev_song, next_song):
        next_segment = AudioSegment.from_file(next_song.file_location)[
            next_song.start_pos:next_song.end_post]
        if prev_song is None:
            return next_segment[:-self.merge_time]
        prev_segment = AudioSegment.from_file(prev_song.file_location)[
            prev_song.start_pos:prev_song.end_post]
        return prev_segment[-self.merge_time:].append(
            next_segment[:-self.merge_time],
            crossfade=self.merge_time)

    def write_sample(self, sample):
        f_name = None
        with NamedTemporaryFile("w+b", suffix=".mp3", delete=False) as f:
            sample.export(f.name, format="mp3")
            f_name = f.name
        with open(f_name, 'rb') as input_f, open(self.output, 'wb') as output:
            buf = True
            while buf:
                buf = input_f.read(4096)
                if buf:
                    output.write(buf)


class InfJukeboxTransitioner(Transitioner):
    def __init__(self, output, segment_size=30):
        self.output = output
        self.segment_size = segment_size

    def merge(self, prev_song, next_song):
        """
        Given two song objects, find the most similar frame in the upcoming
        segments and transition the songs at that frame creating new
        segment.
        Returns the next segment to stream.
        Note: next_song can be the same as prev_song, the next segment of this
              song is returned in this case.
        """
        # Get the next *segment_size* bounding frames from the previous /
        # current song.
        seg_start, seg_end = prev_song.next_segment(self.segment_size)

        # Check if the next song is the same as the current song.
        if prev_song.file_location is next_song.file_location:
            # If it is the same song, return the next segment.
            return prev_song.time_series[seg_start:seg_end]
        else:
            # If it's not the same song, compare both songs and find similar
            # frames to transition on. These are looked for in the upcoming
            # segment of the current song and the first *segment_size* of the
            # next song.
            prev_frame, next_frame = self.find_similar_frames(prev_song, next_song,
                                                         seg_start, seg_end)
            # When a frame to transition on in the current song is found,
            # calculate the time (in seconds) that is between the start of the
            # next segment of this song and the found frame.
            prev_song_time = prev_song.time_delta(seg_start, prev_frame)
            # When above time in seconds is found, it can be subtracted from
            # the segment size to find the remaining time to be filled by the
            # next song. Now calculate to what frame the next song should go.
            final_frame = next_song.frame_to_segment_time(self.segment_size,
                                                          prev_song_time,
                                                          next_frame)

            return np.append(prev_song.time_series[seg_start:prev_frame],
                             next_song.time_series[next_frame:final_frame])

    def find_similar_frames(self, prev_song, next_song, seg_start, seg_end):
        """
        Find a similar frame in the previous (current) and the next song. Only
        frames in the next segment of the current song and the first segment
        of the next song will be taken into account.
        Returns a tuple of the frames (frame_prev_song, frame_next_song) that
        are found most similar.
        """
        prev_bt = prev_song.beat_track_in_segment(seg_start, seg_end)
        next_start, next_end = next_song.next_segment(self.segment_size,
                                                      begin=True)
        next_bt = next_song.beat_track_in_segment(next_start, next_end)

        highest = -9999999
        highest_n = 0
        highest_p = 0
        for p in range(len(prev_bt) - 1):
            for n in range(len(next_bt) - 1):
                corr = np.correlate(prev_song.time_series[prev_bt[p]:prev_bt[p + 1]],
                                    next_song.time_series[next_bt[n]:next_bt[n + 1]],
                                    mode="valid")
                # experiment with highest vs lowest corr!
                if corr[0] >= highest:
                    highest = corr[0]
                    highest_n = next_bt[n]
                    highest_p = prev_bt[p]
        print(highest_p, highest_n)
        return highest_p, highest_n

    def write_sample(self, sample):
        librosa.output.write_wav("tests/test_data/songs/output.wav",
                                 sample,
                                 SAMPLING_RATE,
                                 norm=False)
