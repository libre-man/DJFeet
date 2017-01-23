from collections import namedtuple
import re

PARAM_REGEX = re.compile(r"param[ \w]* (?P<name>[\*\w]+):", re.S)


def _parse_long_docstring(lines):
    """Parse the long part (after the first newline) of a docstring.

    :returns: A tuple of the long description of the function, the parameters
              and the return value in this order.
    """
    returns = ""
    long_description = []
    params = {}

    opt_param, opt_return = range(2)
    in_desc = True
    desc = name = cur = None
    skip = False

    for line in lines.split('\n') + [':end:']:
        line = line.strip()
        if not line:
            continue
        if in_desc:
            if line[0] == ":":
                in_desc = False
            else:
                long_description.append(line)
                continue

        if line[0] == ':':
            skip = False

            if cur == opt_param:
                params[name] = " ".join(desc).strip()
            elif cur == opt_return:
                returns = " ".join(desc).strip()

            line = line[1:]

            if line.startswith('param') or line.startswith('returns'):
                cur = opt_return
                if line[0] == 'p':
                    name = PARAM_REGEX.findall(line)[0]
                    cur = opt_param
                line = line[line.find(':') + 1:].strip()
                desc = [line]
            else:
                skip = True

        elif not skip:
            desc.append(line)

    return long_description, params, returns


def parse_docstring(docstring):
    """Parse the docstring into its components.
    :returns: a dictionary of form
              {
                  "short": ...,
                  "long": ...,
                  "params": {"name": doc for each param},
                  "returns": ...
              }
    """

    short_description = returns = ""
    long_description = []
    params = {}

    if docstring:
        lines = docstring.split("\n", 1)
        short_description = lines[0]

        if len(lines) > 1:
            long_description, params, returns = _parse_long_docstring(lines[1])

    return {
        "short": short_description,
        "long": " ".join(long_description),
        "params": params,
        "returns": returns
    }


SongStruct = namedtuple("SongStruct", "file_location start_pos end_pos")

EPSILON = 0.000001


def get_all_subclasses(baseclass):
    todo = [baseclass]
    res = set()
    while todo:
        for cls in todo.pop().__subclasses__():
            res.add(cls)
            todo.append(cls)
    return res
