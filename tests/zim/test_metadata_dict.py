import pytest
from zimscraperlib.zim.metadata_dict import MetadataDict


def test_init_default_value():
    metadata = MetadataDict()
    assert metadata["Language"] != ""
    assert metadata["Date"] != ""
    assert metadata["Title"] == ""
    assert metadata["Name"] == ""
    assert metadata["Creator"] == ""
    assert metadata["Description"] == ""
    assert metadata["Illustration_48x48@1"] == ""
    assert metadata["Publisher"] == ""


def test_update_value():
    metadata = MetadataDict()
    metadata["Title"] = "Test Tile"
    metadata["Name"] = "Test Name"
    metadata["Creator"] = "Test Creator"
    metadata["Description"] = "Test Description"
    metadata["Illustration_48x48@1"] = "Test Illustration_48x48@1"
    metadata["Publisher"] = "Wikipedia user Foobar"

    assert metadata["Title"] == "Test Tile"
    assert metadata["Name"] == "Test Name"
    assert metadata["Creator"] == "Test Creator"
    assert metadata["Description"] == "Test Description"
    assert metadata["Illustration_48x48@1"] == "Test Illustration_48x48@1"


def test_keys_are_capitalized():
    metadata_dict = MetadataDict()
    metadata_dict["language"] = "zho"
    assert metadata_dict["Language"] == "zho"
    pass


def test_check_all_mandatory_values():
    metadata = MetadataDict()
    assert metadata.mandatory_values_all_set == False
    assert len(metadata.unset_keys) > 0
    metadata["Title"] = "Test Tile"
    metadata["Name"] = "Test Name"
    metadata["Creator"] = "Test Creator"
    metadata["Description"] = "Test Description"
    metadata["Illustration_48x48@1"] = "Test Illustration_48x48@1"
    metadata["Publisher"] = "Wikipedia user Foobar"
    assert metadata.mandatory_values_all_set == True
    assert len(metadata.unset_keys) == 0
