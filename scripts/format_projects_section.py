from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.parsers.latex_assembler import inject_resume_personalization


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject formatted project entries into a LaTeX template.")
    parser.add_argument("--template", required=True, help="Path to the LaTeX template file.")
    parser.add_argument("--projects-json", required=True, help="Path to a JSON file with a top-level 'projects' array.")
    parser.add_argument("--output", required=True, help="Path for the rendered LaTeX output.")
    args = parser.parse_args()

    template_path = Path(args.template)
    projects_path = Path(args.projects_json)
    output_path = Path(args.output)

    template_text = template_path.read_text(encoding="utf-8")
    payload = json.loads(projects_path.read_text(encoding="utf-8"))
    rendered = inject_resume_personalization(
        template_text,
        str(payload.get("headline", "")),
        payload.get("skills", []),
        payload.get("projects", []),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
