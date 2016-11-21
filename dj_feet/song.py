from pydub import AudioSegment

# Step size of streaming in miliseconds
STEP_SIZE = 30000

class Song:
    def __init__(self, file_location, start_pos, progress=0):
        self.file_location = file_location
        self.start_pos = start_pos
        self.progress = progress

    def add_progress(addition=1):
        self.progress += addition

    def get_next_segment():
        """
        Return the next segment of the sample. The length of this segment
        is defined in the STEP_SIZE constant.
        """
        return AudioSegment.from_file(next_song.file_location)
               [self.start_pos + STEP_SIZE * self.progress:
                self.start_pos + STEP_SIZE * (self.progress + 1)]
