from pathlib import Path

from app import demo_workflow


def test_demo_workflow_runs_without_real_publishing(monkeypatch, tmp_path):
    called = {}
    recipe = {
        "map_title": "Parcel Flood in Concord",
        "selected_layers": [{"layer_key": "parcels"}],
    }
    webmap = {"title": "Parcel Flood in Concord", "operationalLayers": []}
    packet_path = tmp_path / "review_packet"
    adjusted_path = tmp_path / "adjusted_packet"
    packet_path.mkdir()
    adjusted_path.mkdir()
    template_path = packet_path / "adjustments.template.yaml"

    monkeypatch.setattr(demo_workflow, "build_recipe", lambda prompt: recipe)
    monkeypatch.setattr(demo_workflow, "build_webmap_json", lambda built_recipe: webmap)
    monkeypatch.setattr(demo_workflow, "save_webmap_json", lambda built_webmap: tmp_path / "webmap.json")
    monkeypatch.setattr(
        demo_workflow,
        "build_review_packet",
        lambda prompt: {"recipe": recipe, "webmap_json": webmap},
    )
    monkeypatch.setattr(demo_workflow, "save_review_packet", lambda prompt, built_recipe, built_webmap: packet_path)
    monkeypatch.setattr(demo_workflow, "create_adjustment_template", lambda path: template_path)
    monkeypatch.setattr(demo_workflow, "apply_adjustments_to_review_packet", lambda packet, template: adjusted_path)
    monkeypatch.setattr(demo_workflow, "validate_adjusted_packet", lambda path: {"is_valid": True})
    monkeypatch.setattr(demo_workflow, "record_request_history", lambda **kwargs: 1)

    def fake_publish(path, dry_run=True, confirm_publish=False):
        called["path"] = Path(path)
        called["dry_run"] = dry_run
        called["confirm_publish"] = confirm_publish
        return {
            "status": "dry_run",
            "created_item": False,
            "published": False,
            "shared_public": False,
            "shared_organization": False,
        }

    monkeypatch.setattr(demo_workflow, "publish_webmap_draft", fake_publish)

    result = demo_workflow.run_demo_workflow(ui_port=8010)

    assert result["real_publish_attempted"] is False
    assert result["publish_result"]["created_item"] is False
    assert result["publish_result"]["published"] is False
    assert called["dry_run"] is True
    assert called["confirm_publish"] is False
    assert result["preview_url"].startswith("http://127.0.0.1:8010/preview")
