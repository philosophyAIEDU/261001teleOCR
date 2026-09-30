from backend.ocr.layout import ContentBlock, parse_layout_output


def test_parses_rectangles_and_polygons() -> None:
    out = (
        "<box:100 200 300 400><label:title><up>\n"
        "<box:0 0 1000 0 1000 1000 0 1000 0 500><label:table><right>\n"
    )
    blocks = parse_layout_output(out)
    assert [b.type for b in blocks] == ["title", "table"]
    assert blocks[0].points == [[0.1, 0.2], [0.3, 0.2], [0.3, 0.4], [0.1, 0.4]]
    assert blocks[0].angle == 0
    assert len(blocks[1].points) == 5
    assert blocks[1].angle == 90
    assert blocks[1].bbox == (0.0, 0.0, 1.0, 1.0)


def test_skips_invalid_lines() -> None:
    out = "\n".join(
        [
            "garbage line",
            "<box:1 2 3><label:text><up>",  # 좌표 개수가 홀수
            "<box:1 2 3 4000><label:text><up>",  # 범위 밖
            "<box:10 20 30 40><label:text><down>",
        ]
    )
    blocks = parse_layout_output(out)
    assert len(blocks) == 1 and blocks[0].angle == 180


def test_unknown_label_and_missing_angle() -> None:
    blocks = parse_layout_output("<box:30 40 10 20><label:Weird><?>")
    assert blocks[0].type == "unknown"
    assert blocks[0].angle is None
    # 좌표가 뒤집혀 있어도 정렬됩니다.
    assert blocks[0].bbox == (0.01, 0.02, 0.03, 0.04)


def test_to_dict_has_korean_label() -> None:
    block = ContentBlock(type="seal", points=[[0, 0], [1, 0], [1, 1], [0, 1]], angle=270)
    data = block.to_dict()
    assert data["label"] == "도장"
    assert data["bbox"] == [0, 0, 1, 1]


def test_empty_output() -> None:
    assert parse_layout_output("") == []
