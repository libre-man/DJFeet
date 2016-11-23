from .transitioners import InfJukeboxTransitioner
from .song import Song
def main(debug=True):
    test()

def test():
    song1 = Song("tests/test_data/songs/BachGavotteShort.mp3", 0)
    song2 = Song("tests/test_data/songs/PurcellSongSpinShort.mp3", 0)
    trans = InfJukeboxTransitioner(0)
    trans.write_sample(trans.merge(song1, song2))
