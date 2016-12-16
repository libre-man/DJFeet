# -*- coding: utf-8 -*-
import librosa
from pydub import AudioSegment
from .song import Song
from tempfile import NamedTemporaryFile
import numpy as np


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
            transition, prev_frame, next_frame = self.combine_similar_frames(
                prev_song, next_song, seg_start, seg_end)

            # When a frame to transition on in the current song is found,
            # calculate the time (in seconds) that is between the start of the
            # next segment of this song and the found frame.
            prev_song_time = prev_song.time_delta(seg_start, prev_frame)
            # When above time in seconds is found, it can be subtracted from
            # the segment size to find the remaining time to be filled by the
            # next song. Now calculate to what frame the next song should go.
            final_frame = next_song.frame_to_segment_time(
                self.segment_size, prev_song_time, next_frame)

            return np.append(
                np.append(prev_song.time_series[seg_start:prev_frame],
                          transition),
                next_song.time_series[next_frame:final_frame])

    def combine_similar_frames(self, prev_song, next_song, seg_start, seg_end):
        """
        Find a similar frame in the previous (current) and the next song. Only
        frames in the next segment of the current song and the first segment
        of the next song will be taken into account.
        Returns a tuple of the frames (frame_prev_song, frame_next_song) that
        are found most similar.
        """
        prev_bt = prev_song.beat_track_in_segment(seg_start, seg_end)
        next_start, next_end = next_song.next_segment(
            self.segment_size, begin=True)
        next_bt = next_song.beat_track_in_segment(next_start, next_end)

        highest = -9999999
        highest_n = 0
        highest_p = 0
        for p in range(len(prev_bt) - 2):
            for n in range(len(next_bt) - 2):
                corr = np.correlate(
                    prev_song.time_series[prev_bt[p]:prev_bt[p + 1]],
                    next_song.time_series[next_bt[n]:next_bt[n + 1]],
                    mode="valid")
                # TODO: Optimize the way to interpret the cross correlation!!
                if corr[0] >= highest:
                    highest = corr[0]
                    highest_n = n
                    highest_p = p
        print(highest_p, highest_n)
        transition = self.fade_frames(prev_song, prev_bt, highest_p, next_song,
                                      next_bt, highest_n)
        return transition, prev_bt[highest_p - 1], next_bt[highest_n + 1]

    def fade_frames(self, prev_song, prev_bt, p, next_song, next_bt, n):
        """
        Lineare crossfade
        """
        prev_seg = prev_song.time_series[prev_bt[p]:prev_bt[p + 1]]
        next_seg = next_song.time_series[next_bt[n]:next_bt[n + 1]]
        final_seg = []
        prev_delta = 1 / len(prev_seg)
        next_delta = 1 / len(next_seg)
        for p in range(len(prev_seg)):
            final_seg.append(prev_seg[p] * (1 - prev_delta * p))

        for n in range(len(next_seg)):
            if n > len(prev_seg) - 1:
                final_seg.append(next_seg[n] * (prev_delta * n))
            else:
                final_seg[n] += next_seg[n] * (prev_delta * n)

        return final_seg

    def write_sample(self, sample):
        librosa.output.write_wav(self.output, sample, sr=22050, norm=False)
