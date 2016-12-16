from .transitioners import InfJukeboxTransitioner
from .song import Song
def main(debug=True):
    pass

def test():
    song1 = Song("tests/test_data/songs/song1.wav", 0)
    song2 = Song("tests/test_data/songs/song2.wav", 0)
    trans = InfJukeboxTransitioner("tests/test_data/songs/output.wav", segment_size=30)
    trans.write_sample(trans.merge(song1, song2))
