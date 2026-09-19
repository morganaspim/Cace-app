from __future__ import annotations

from cace_studio.app import build_registry
from cace_studio.public_help import (
    build_public_help_catalog,
    render_markdown,
    validate_public_help,
)


def test_public_help_covers_every_registered_module():
    catalog = build_public_help_catalog()
    assert catalog["module_count"] == len(build_registry().classes())
    assert len(catalog["modules"]) == catalog["module_count"]


def test_every_feature_has_two_examples():
    catalog = build_public_help_catalog()
    assert catalog["features"]
    assert all(len(item["examples"]) >= 2 for item in catalog["features"])


def test_every_module_has_two_direct_and_two_combined_examples():
    catalog = build_public_help_catalog()
    assert all(len(item["examples"]) >= 2 for item in catalog["modules"])
    assert all(len(item["connection_examples"]) >= 2 for item in catalog["modules"])


def test_public_help_exposes_only_safe_contract_fields():
    catalog = build_public_help_catalog()
    forbidden = {
        "module_id",
        "source_path",
        "class_name",
        "theorem",
        "implementation",
        "default",
        "description",
        "assumptions",
    }
    for module in catalog["modules"]:
        assert forbidden.isdisjoint(module)
        assert module["name"]
        assert module["category"]
        assert "inputs" in module
        assert "outputs" in module
        assert "parameters" in module
        assert all("default" not in item for item in module["parameters"])


def test_rendered_help_passes_leakage_policy():
    catalog = build_public_help_catalog()
    rendered = render_markdown(catalog)
    validate_public_help(catalog, rendered)
    assert "proprietary" in rendered.casefold()
    assert "custom internal mathematics" in rendered.casefold()


def test_connection_language_does_not_claim_scientific_validity():
    catalog = build_public_help_catalog()
    joined = "\n".join(
        example
        for module in catalog["modules"]
        for example in module["connection_examples"]
    )
    assert "type/unit" in joined
    assert "scientific" in joined
