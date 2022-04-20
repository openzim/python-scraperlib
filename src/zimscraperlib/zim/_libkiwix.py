r""" [INTERNAL] libkiwix's internal features copies

CAUTION: this is __not__ part of zimscraperlib's API. Don't use outside scraperlib!

Following methods are direct copies of libkiwix's for which there is a need to
in scraperlib. The goal is not to reimplement similar features but to stick as much
as possible to the original source code so that upstream changes can be backported
easily. Hence the unexpected method names and formatting.

https://github.com/kiwix/libkiwix/blob/master/src/reader.cpp
https://github.com/kiwix/libkiwix/blob/master/src/tools/archiveTools.cpp
"""

import io
from collections import namedtuple
from typing import Dict, Optional, Tuple

MimetypeAndCounter = namedtuple("MimetypeAndCounter", ["mimetype", "value"])
CounterMap = Dict[type(MimetypeAndCounter.mimetype), type(MimetypeAndCounter.value)]


def getline(src: io.StringIO, delim: Optional[bool] = None) -> Tuple[bool, str]:
    """C++ stdlib getline() ~clone

    Reads `src` until it finds `delim`.
    returns whether src is EOF and the extracted string (delim excluded)"""
    output = ""
    if not delim:
        return True, src.read()

    char = src.read(1)
    while char:
        if char == delim:
            break
        output += char
        char = src.read(1)
    return char == "", output


def readFullMimetypeAndCounterString(src: io.StringIO) -> Tuple[bool, str]:
    """read a single mimetype-and-counter string from source

    Returns whether the source is EOF and the extracted string (or empty one)"""
    params = ""
    eof, mtcStr = getline(src, ";")
    if mtcStr.find("=") == -1:
        while params.count("=") != 2:
            eof, params = getline(src, ";")
            if params.count("=") == 2:
                mtcStr += ";" + params
            if eof:
                break
    return eof, mtcStr


def parseASingleMimetypeCounter(string: str) -> MimetypeAndCounter:
    """MimetypeAndCounter from a single mimetype-and-counter string"""
    k: int = string.rfind("=")
    if k != len(string) - 1:
        mimeType = string[:k]
        counter = string[k + 1 :]
        if counter:
            try:
                return MimetypeAndCounter(mimeType, int(counter))
            except ValueError:
                pass  # value is not castable to int
    return MimetypeAndCounter("", 0)


def parseMimetypeCounter(
    counterData: str,
) -> CounterMap:
    """Mapping of MIME types with count for each from ZIM Counter metadata string"""
    counters = dict()
    ss = io.StringIO(counterData)
    eof = False
    while not eof:
        eof, mtcStr = readFullMimetypeAndCounterString(ss)
        mtc = parseASingleMimetypeCounter(mtcStr)
        if mtc.mimetype:
            counters.update([mtc])
    ss.close()
    return counters


def getArticleCount(counterMap: CounterMap):
    """Get the count of articles which can be indexed/displayed"""
    counter = 0
    for mimetype, count in counterMap.items():
        if mimetype.startswith("text/html"):
            counter += count

    return counter


def getMediaCount(counterMap: CounterMap) -> int:
    """Get the count of medias content in the ZIM file"""
    counter = 0
    for mimetype, count in counterMap.items():
        if (
            mimetype.startswith("image/")
            or mimetype.startswith("video/")
            or mimetype.startswith("audio/")
        ):
            counter += count

    return counter
