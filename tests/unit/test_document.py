import md2cf.document as doc


def test_page_get_content_hash():
    p = doc.Page(title="test title", body="test content")

    assert p.get_content_hash() == "1eebdf4fdc9fc7bf283031b93f9aef3338de9052"
