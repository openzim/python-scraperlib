r""" [INTERNAL] libkiwix's internal features copies

CAUTION: this is __not__ part of zimscraperlib's API. Don't use outside scraperlib!

Following methods are direct copies of libkiwix's for which there is a need to
in scraperlib. The goal is not to reimplement similar features but to stick as much
as possible to the original source code so that upstream changes can be backported
easily. Hence the unexpected method names and formatting.

https://github.com/kiwix/libkiwix/blob/master/src/reader.cpp
https://github.com/kiwix/libkiwix/blob/master/src/tools/archiveTools.cpp
https://github.com/kiwix/libkiwix/blob/master/src/tools/otherTools.cpp
"""

from __future__ import annotations

import io
from collections import namedtuple
from typing import Dict

MimetypeAndCounter = namedtuple("MimetypeAndCounter", ["mimetype", "value"])
CounterMap = Dict[
    type(MimetypeAndCounter.mimetype), type(MimetypeAndCounter.value)  # pyright: ignore
]


def getline(src: io.StringIO, delim: bool | None = None) -> tuple[bool, str]:
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


def readFullMimetypeAndCounterString(
    src: io.StringIO,
) -> tuple[bool, str]:
    """read a single mimetype-and-counter string from source

    Returns whether the source is EOF and the extracted string (or empty one)"""
    params = ""
    eof, mtcStr = getline(src, ";")  # pyright: ignore
    if mtcStr.find("=") == -1:
        while params.count("=") != 2:  # noqa: PLR2004
            eof, params = getline(src, ";")  # pyright: ignore
            if params.count("=") == 2:  # noqa: PLR2004
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
        try:
            return MimetypeAndCounter(mimeType, int(counter))
        except ValueError:
            pass  # value is not castable to int
    return MimetypeAndCounter("", 0)


def parseMimetypeCounter(
    counterData: str,
) -> CounterMap:
    """Mapping of MIME types with count for each from ZIM Counter metadata string"""
    counters = {}
    ss = io.StringIO(counterData)
    eof = False
    while not eof:
        eof, mtcStr = readFullMimetypeAndCounterString(ss)
        mtc = parseASingleMimetypeCounter(mtcStr)
        if mtc.mimetype:
            counters.update([mtc])
    ss.close()
    return counters


def convertTags(tags_str: str) -> list[str]:
    """List of tags expanded with libkiwix's additional hints for pic/vid/det/index"""
    tags = tags_str.split(";")
    tagsList = []
    picSeen = vidSeen = detSeen = indexSeen = False
    for tag in tags:
        # not upstream
        if not tag:
            continue
        picSeen |= tag == "nopic" or tag.startswith("_pictures:")
        vidSeen |= tag == "novid" or tag.startswith("_videos:")
        detSeen |= tag == "nodet" or tag.startswith("_details:")
        indexSeen |= tag.startswith("_ftindex")

        if tag == "nopic":
            tagsList.append("_pictures:no")
        elif tag == "novid":
            tagsList.append("_videos:no")
        elif tag == "nodet":
            tagsList.append("_details:no")
        elif tag == "_ftindex":
            tagsList.append("_ftindex:yes")
        else:
            tagsList.append(tag)

    if not indexSeen:
        tagsList.append("_ftindex:no")
    if not picSeen:
        tagsList.append("_pictures:yes")
    if not vidSeen:
        tagsList.append("_videos:yes")
    if not detSeen:
        tagsList.append("_details:yes")
    return tagsList
