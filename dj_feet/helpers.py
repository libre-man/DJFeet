from collections import namedtuple
import re

PARAM_OR_RETURNS_REGEX = re.compile(":(?:param|returns)")
RETURNS_REGEX = re.compile(":returns: (?P<doc>.*)", re.S)
PARAM_REGEX = re.compile(r":param (?P<name>[\*\w]+): (?P<doc>.*?)" +
                         r"(?:(?=:param)|(?=:return)|(?=:raises)|\Z)", re.S)


def reindent(string):
    return "\n".join(l.strip() for l in string.strip().split("\n"))


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

    short_description = long_description = returns = ""
    params = {}

    if docstring:
        lines = docstring.split("\n", 1)
        short_description = lines[0]

        if len(lines) > 1:
            long_description = lines[1].strip()

            params_returns_desc = None

            match = PARAM_OR_RETURNS_REGEX.search(long_description)
            if match:
                long_desc_end = match.start()
                params_returns_desc = long_description[long_desc_end:].strip()
                long_description = long_description[:long_desc_end].rstrip()

            if params_returns_desc:
                params = {
                    name.strip(): doc.strip()
                    for name, doc in PARAM_REGEX.findall(params_returns_desc)
                }

                match = RETURNS_REGEX.search(params_returns_desc)
                if match:
                    returns = reindent(match.group("doc"))

    return {
        "short": short_description,
        "long": "\n".join(line for line in long_description.split("\n")
                          if not line.strip().startswith(":")).rstrip(),
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
