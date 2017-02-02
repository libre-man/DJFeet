# -*- coding: utf-8 -*-

import librosa
import os
import datetime
import numpy as np
import tempfile
import logging
import pydub

l = logging.getLogger(__name__)


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

    def __init__(self,
                 output_folder,
                 segment_size=30,
                 fade_time=6,
                 fade_steps=1000):
        """Create a new InfJukeboxTransitioner instance.

        :param output_folder: The folder to write the new part to.
        :type output_folder: string
        :param segment_size: The length (in seconds) of a part. (default=30)
        :param int fade_time: The total time in seconds a fade should last.
        :param int fade_steps: The amount of samples to merge at the same time
                               during the coarse fading.
        :type segment_size: int
        """
        self.output_folder = output_folder
        self.segment_size = segment_size
        self.segment_delta = datetime.timedelta(seconds=segment_size)
        self.part_no = 0
        self.fade_time = fade_time
        self.fade_steps = fade_steps

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
            if self.part_no > 0:
                l.critical('prev_song was None while part_no was > 0')
            else:
                l.debug('This is the first merge.')
            prev_song = next_song

        # Check whether the previous song still has segment size of time left
        if prev_song.file_location == next_song.file_location:
            # We check op times two as we need 30 seconds for now and we might
            # need at most 30 seconds to merge to another song after this
            # merge. If we loop again after this iteration this check gets
            # executed again.
            if not prev_song.segment_size_left(self.segment_size * 2):
                l.critical("We do not have enough time for '%s' (next song)." +
                           " song.curr_time: %d", prev_song.file_location,
                           prev_song.curr_time)
                raise ValueError("Song time exceeded")
        else:
            # We know we still have at least 30 seconds of prev_song left. See
            # check above. We need at least 60 seconds of the next song: 30 for
            # this merge and at most 30 seconds if we change songs after this.
            # If we loop after this merge we get in the previous check.
            if not next_song.segment_size_left(self.segment_size * 2):
                l.critical("We do not have enough time for '%s' (next song)." +
                           " song.curr_time: %d", next_song.file_location,
                           next_song.curr_time)
                raise ValueError("Song time exceeded")

        # Get the next *segment_size* bounding frames from the previous /
        # current song.
        seg_start, seg_end = prev_song.next_segment(self.segment_size)

        l.info("Going from %d to %d index in prev_song", seg_start, seg_end)

        # Check if the next song is the same as the current song.
        if prev_song.file_location == next_song.file_location:
            l.debug("Merging the same songs: appending")
            # If it is the same song, return the next segment.
            next_song.curr_time = prev_song.curr_time + self.segment_size
            return (prev_song.time_series[seg_start:seg_end],
                    self.segment_size)
        else:
            l.info("Merging the two different songs.")
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

            l.debug("Merged from %d to %d for the old song and from %d to" +
                    " %d fro the new song.", seg_start, prev_frame, next_frame,
                    final_frame)

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

        min_prev_sample = librosa.core.time_to_samples(
            [prev_song.curr_time + self.fade_time / 2],
            prev_song.sampling_rate)[0]
        max_prev_sample = librosa.core.time_to_samples(
            [prev_song.curr_time + self.segment_size - self.fade_time / 2],
            prev_song.sampling_rate)[0]
        min_next_sample = librosa.core.time_to_samples(
            [self.fade_time / 2], next_song.sampling_rate)[0]
        max_next_sample = librosa.core.time_to_samples(
            [self.segment_size - self.fade_time / 2],
            next_song.sampling_rate)[0]

        highest = -9999999
        highest_n = 0
        highest_p = 0
        l.debug("Combining similar frames.")
        for p in range(len(prev_bt) - 2):
            if prev_bt[p] < min_prev_sample:
                continue
            if prev_bt[p] >= max_prev_sample:
                break
            for n in range(len(next_bt) - 2):
                if next_bt[n] < min_next_sample:
                    continue
                if next_bt[n] >= max_next_sample:
                    break
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
        transition = self.fade_frames(prev_song, prev_bt[highest_p], next_song,
                                      next_bt[highest_n])

        l.info("Similar frames found, old: %d, new: %d.", highest_p, highest_n)
        return transition, prev_bt[highest_p - 1], next_bt[highest_n + 1]

    def fade_frames(self, prev_song, prev_mid_sample, next_song,
                    next_mid_sample):
        """Create a transition between two songs given a matching beat.

        Use coarse fading to create a (smooth) transition between two songs
        given a beat that matches in both songs. An array containing the
        created transition will be returned.

        :param dj_feet.song.Song prev_song: The song that is currently playing.
        :param int prev_mid_sample: The sample index of the prev_song that
                                    should be in the middle of the merge.
        :param dj_feet.song.Song next_song: The song to play after prev_song.
        :param int next_mid_sample: The sample index of the next_song that
                                    should be in the middle of the merge.
        :returns: An audio array that is the fade in and fade out from
                  prev_song to next_song.
        :rtype: np.array
        """
        sample_offset = librosa.core.time_to_samples([self.fade_time / 2],
                                                     prev_song.sampling_rate)
        prev_seg = np.array(prev_song.time_series[
            prev_mid_sample - sample_offset:prev_mid_sample + sample_offset])
        next_seg = np.array(next_song.time_series[
            next_mid_sample - sample_offset:next_mid_sample + sample_offset])

        final_seg = np.array([])
        delta = 1 / len(prev_seg)

        if len(prev_seg) != len(next_seg):
            l.critical("Segments are not of the same length during fading." +
                       " (%d and %d)" + "Next starts at %d and ends at %d",
                       len(prev_seg),
                       len(next_seg), next_mid_sample - sample_offset,
                       next_mid_sample + sample_offset)

        for p in range(0, len(prev_seg), self.fade_steps):
            end = min(p + self.fade_steps, len(prev_seg))
            final_seg = np.append(final_seg, prev_seg[p:end] * (1 - delta * (
                (end + p) / 2)))

        for n in range(0, len(next_seg), self.fade_steps):
            end = min(n + self.fade_steps, len(next_seg))
            final_seg[n:end] += next_seg[n:end] * (delta * ((end + n) / 2))

        return final_seg

    def write_sample(self, sample):
        """Write the given sample to the output stream.

        Write a given sample to the output stream. This is defined by the set
        output folder when intializing the InfJukeboxTransitioner instance. As
        a side-effect, a WAV file will be written in addition to the MP3 file.

        :param sample: The created part / sample to write.
        :type sample: np.array
        """
        l.info("Writing part %d to %s.", self.part_no, self.output_folder)
        with tempfile.NamedTemporaryFile() as wavfile:
            mp3file = os.path.join(self.output_folder,
                                   "part{}.mp3".format(self.part_no))
            l.debug("Using %s as wavfile and %s as mp3 file", wavfile.name,
                    mp3file)

            librosa.output.write_wav(
                wavfile.name, sample, sr=22050, norm=False)
            wavfile.flush()
            pydub.AudioSegment.from_wav(wavfile.name).export(
                mp3file, format='mp3')

        l.debug("Wrote mp3 file.")
        self.part_no += 1
