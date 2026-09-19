from __future__ import annotations

from cace_studio.public_help import (
    build_public_help_catalog,
    render_markdown,
    validate_public_help,
)


def main() -> int:
    catalog = build_public_help_catalog()
    rendered = render_markdown(catalog)
    validate_public_help(catalog, rendered)
    print(
        "CACE_PUBLIC_HELP_OK "
        f"features={catalog['feature_count']} modules={catalog['module_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
