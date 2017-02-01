# -*- coding: utf-8 -*-

import librosa
import os
import datetime
import numpy as np
import tempfile
import pydub


class Transitioner:
    """This is the base Transitioner class.

    You should not use this class directly but should inherit from this class
    if you want to implement a new picker. A subclass should override all
    public methods of this class.
    """
    def __init__(self):
        """The initializer of the base Transitioner class.

        This function does nothing at the moment
        """
        pass

    def merge(self, prev_song, next_song):
        """Merge two given songs to one sample / part.

        :param prev_song: The song that is currently playing.
        :type prev_song: dj_feet.song.Song
        :param next_song: The song to play next, after prev_song. To not change
                          songs, next_song should be the same as prev_song.
        :type next_song: dj_feet.song.Song
        :rtype: (dj_feet.song.Song, int)
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")

    def write_sample(self, sample):
        """Write the given sample to the output stream.

        :param sample: The created part / sample to write.
        :type sample: np.array
        """
        raise NotImplementedError(
            "This function should be overridden by the subclass")


class InfJukeboxTransitioner(Transitioner):
    """A Transitioner based on the Infinite Jukebox concept.

    This Transioner merges two distinct songs to form a song part containing a
    smooth transition between both songs. To achieve this, a similar beat in
    both songs is found (beatmatching). This beat is ultimately the transition
    between the songs, this is created by a coarse fade.
    """
    def __init__(self, output_folder, segment_size=30):
        """Create a new InfJukeboxTransitioner instance.

        :param output_folder: The folder to write the new part to.
        :type output_folder: string
        :param segment_size: The length (in seconds) of a part. (default=30)
        :type segment_size: int
        """
        self.output_folder = output_folder
        self.segment_size = segment_size
        self.segment_delta = datetime.timedelta(seconds=segment_size)
        self.part_no = 0

    def merge(self, prev_song, next_song):
        """Merge two songs together.

        Given two songs, a new part / sample will be created with a transition
        of these songs. If both given songs are the same, no transition will be
        needed. If they are not, the best beat is found using beatmatching and
        both songs are merged at this beat using coarse fading. This function
        will return a tuple containg the new part and the time (in seconds from
        the beginning of the part) the transition takes place. (so, that 30 -
        this time is the length of the next song played in the created part)

        :param prev_song: The song that is currently playing.
        :type prev_song: dj_feet.song.Song
        :param next_song: The song to play next, after prev_song. To not change
                          songs, next_song should be the same as prev_song.
        :type next_song: dj_feet.song.Song
        :rtype: (np.array, int)
        """
        if prev_song is None:
            print('Doing the first merge.')
            prev_song = next_song

        # Check whether the previous song still has segment size of time left
        if not prev_song.segment_size_left(self.segment_size):
            print("Song time exceeded")
            raise ValueError("Song time exceeded")

        # Get the next *segment_size* bounding frames from the previous /
        # current song.
        seg_start, seg_end = prev_song.next_segment(self.segment_size)

        print("Going from {} to {} segments".format(seg_start, seg_end))

        # Check if the next song is the same as the current song.
        if prev_song.file_location == next_song.file_location:
            print("Merging the same songs: appending")
            # If it is the same song, return the next segment.
            next_song.curr_time = prev_song.curr_time + self.segment_size
            return (prev_song.time_series[seg_start:seg_end],
                    self.segment_size)
        else:
            print("Merging the two different songs")
            # If it's not the same song, compare both songs and find similar
            # frames to transition on. These are looked for in the upcoming
            # segment of the current song and the first *segment_size* of the
            # next song.
            transition, prev_frame, next_frame = self.combine_similar_frames(
                prev_song, next_song, seg_start, seg_end)

            # When a frame to transition on in the current song is found,
            # calculate the time (in seconds) that is between the start of the
            # next segment of this song and the found frame.
            prev_song_time_delta = prev_song.time_delta(seg_start, prev_frame)

            # When above time in seconds is found, it can be subtracted from
            # the segment size to find the remaining time to be filled by the
            # next song. Now calculate to what frame the next song should go.

            final_frame = next_song.frame_to_segment_time(
                self.segment_size - prev_song_time_delta, next_frame)

            next_song.curr_time = next_song.time_delta(0, final_frame)

            # TODO: No errors with mixing frames / segments?
            prev_part = np.append(prev_song.time_series[seg_start:prev_frame],
                                  transition)
            next_part = next_song.time_series[next_frame:final_frame]
            song_array = np.append(prev_part, next_part)
            merge_time = next_song.time_delta(seg_start, prev_frame)
            return (song_array, merge_time)

    def combine_similar_frames(self, prev_song, next_song, seg_start, seg_end):
        """
        Find the two most familiar beats in two given songs (beatmatching).

        Find a similar frame in the previous (current) and the next song. Only
        frames in the next segment of the current song and the first segment
        of the next song will be taken into account. Similarities between
        beats are compared and approximated using cross correlation.
        Returns a tuple of the frames (frame_prev_song, frame_next_song) that
        are found most similar. In addition it returns an the created
        transition.

        :param prev_song: The song that is currently playing.
        :type prev_song: dj_feet.song.Song
        :param next_song: The song to play next, after prev_song.
        :type next_song: dj_feet.song.Song
        :param seg_start: The first sample of the next segment of prev_song.
        :type seg_start: int
        :param seg_end: The final sample of the next segment of prev_song.
        :type seg_end: int
        :rtype: (np.array, int, int)
        """
        prev_bt = prev_song.beat_tracks_in_segment(seg_start, seg_end)
        next_start, next_end = next_song.next_segment(
            self.segment_size, begin=True)
        next_bt = next_song.beat_tracks_in_segment(next_start, next_end)

        highest = -9999999
        highest_n = 0
        highest_p = 0
        for p in range(len(prev_bt) - 2):
            for n in range(len(next_bt) - 2):
                corr = np.correlate(
                    prev_song.time_series[prev_bt[p]:prev_bt[p + 1]],
                    next_song.time_series[next_bt[n]:next_bt[n + 1]],
                    mode="valid")
                # Check whether the average of the array is higher than the
                # highest previous found beat.
                average = np.average(corr)
                if average >= highest:
                    highest = average
                    highest_n = n
                    highest_p = p
        print(highest_p, highest_n)
        transition = self.fade_frames(prev_song, prev_bt, highest_p, next_song,
                                      next_bt, highest_n)
        return transition, prev_bt[highest_p - 1], next_bt[highest_n + 1]

    def fade_frames(self, prev_song, prev_bt, p, next_song, next_bt, n):
        """Create a transition between two songs given a matching beat.

        Use coarse fading to create a (smooth) transition between two songs
        given a beat that matches in both songs. An array containing the
        created transition will be returned.

        :param prev_song: The song that is currently playing.
        :type prev_song: dj_feet.song.Song
        :param prev_bt: Array containing beat indices of prev_song.
        :type prev_bt: int array
        :param p: The index of the beat (found by beatmatching) of prev_song.
        :type p: int
        :param next_song: The song to play next, after prev_song.
        :type next_song: dj_feet.song.Song
        :param next_bt: Array containing beat indices of next_song.
        :type next_bt: int array
        :param n: The index of the beat (found by beatmatching) of next_song.
        :type n: int
        :rtype: np.array
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
                final_seg.append(next_seg[n] * (next_delta * n))
            else:
                final_seg[n] += next_seg[n] * (next_delta * n)

        return final_seg

    def write_sample(self, sample):
        """Write the given sample to the output stream.

        Write a given sample to the output stream. This is defined by the set
        output folder when intializing the InfJukeboxTransitioner instance. As
        a side-effect, a WAV file will be written in addition to the MP3 file.

        :param sample: The created part / sample to write.
        :type sample: np.array
        """
        print("Writing parg {} to {} dir".format(self.part_no,
                                                 self.output_folder))
        with tempfile.NamedTemporaryFile() as wavfile:
            mp3file = os.path.join(self.output_folder,
                                   "part{}.mp3".format(self.part_no))
            librosa.output.write_wav(
                wavfile.name, sample, sr=22050, norm=False)
            wavfile.flush()
            pydub.AudioSegment.from_wav(wavfile.name).export(
                mp3file, format='mp3')
        self.part_no += 1
