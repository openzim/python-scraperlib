import pytest
from zimscraperlib.zim.metadata_dict import MetadataDict


def test_all_are_correct():
    metadata = MetadataDict()
    assert metadata.all_are_set == False
    metadata["Title"] = "Test Tile"
    metadata["name"] = "Test Name"
    metadata["Creator"] = "Test Creator"
    metadata["date"] = "2022-03-09"
    metadata["Description"] = "Test Description"
    assert metadata.all_are_set == False
    metadata["language"] = "eng"
    metadata["Publisher"] = "Test Publisher"
    assert metadata.all_are_set == True
