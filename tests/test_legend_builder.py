from app.map_composer import _legend_symbol_fields


def test_legend_symbol_fields_match_fill_renderer_metadata():
    fields = _legend_symbol_fields(
        {
            "renderer": {
                "symbol": {
                    "type": "esriSFS",
                    "color": [14, 165, 233, 112],
                    "outline": {"style": "esriSLSSolid", "color": [2, 132, 199, 235], "width": 1.8},
                }
            }
        }
    )

    assert fields["fill_color"] == [14, 165, 233, 112]
    assert fields["fill_opacity"] == 0.439
    assert fields["outline_color"] == [2, 132, 199, 235]
    assert fields["outline_opacity"] == 0.922
    assert fields["outline_width"] == 1.8


def test_legend_symbol_fields_match_line_renderer_metadata():
    fields = _legend_symbol_fields({"renderer": {"symbol": {"type": "esriSLS", "color": [31, 41, 55, 245], "style": "esriSLSSolid", "width": 2.8}}})

    assert fields["line_color"] == [31, 41, 55, 245]
    assert fields["line_opacity"] == 0.961
    assert fields["line_style"] == "esriSLSSolid"
    assert fields["line_width"] == 2.8
