from collections import namedtuple

SongStruct = namedtuple("SongStruct", "file_location start_pos end_pos")


def get_all_subclasses(baseclass):
    todo = [baseclass]
    res = set()
    while todo:
        for cls in todo.pop().__subclasses__():
            res.add(cls)
            todo.append(cls)
    return res
