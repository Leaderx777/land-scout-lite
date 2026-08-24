from land_scout.core.market import is_target_county


def test_target_county_matching():
    assert is_target_county("Peoria")
    assert is_target_county("Peoria County")
    assert is_target_county("tazewell")
    assert not is_target_county("Cook")
