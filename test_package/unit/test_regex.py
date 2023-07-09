from md2cf.upsert import CONTENT_HASH_REGEX


def test_hash_messge(mocker):
    """Base case: page doesn't already exist"""
    result = CONTENT_HASH_REGEX.search(
        "hello there [v11dd64d04e0bf92935910a7e73fed39675b1f9a2]"
    )
    assert result is not None
    assert result.group(1) == "11dd64d04e0bf92935910a7e73fed39675b1f9a2"


def test_hash_no_messge(mocker):
    """Base case: page doesn't already exist"""
    result = CONTENT_HASH_REGEX.search("[v11dd64d04e0bf92935910a7e73fed39675b1f9a2]")
    assert result is not None
    assert result.group(1) == "11dd64d04e0bf92935910a7e73fed39675b1f9a2"


def test_hash_no_hash(mocker):
    """Base case: page doesn't already exist"""
    result = CONTENT_HASH_REGEX.search("hi")
    assert result is None
