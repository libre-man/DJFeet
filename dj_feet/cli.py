from .transitioners import InfJukeboxTransitioner
from .song import Song
def main(debug=True):
    test()

def test():
    song1 = Song("tests/test_data/songs/song1.wav", 0)
    song2 = Song("tests/test_data/songs/song1.wav", 0)
    trans = InfJukeboxTransitioner(0, segment_size=30)
    trans.write_sample(song1.time_series)
