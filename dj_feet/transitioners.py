# -*- coding: utf-8 -*-
from pydub import AudioSegment
from .helpers import SongStruct
from tempfile import NamedTemporaryFile


class Transitioner:
    def __init__(self):
        pass

    def merge(self, prev_song, next_song):
        """Merge the two given song structs.
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
