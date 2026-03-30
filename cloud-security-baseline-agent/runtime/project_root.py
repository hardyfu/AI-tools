import os
from pathlib import Path


def resolve_project_root(anchor: str | Path) -> Path:
    env_root = os.getenv("BASELINE_AGENT_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()

    anchor_path = Path(anchor).resolve()
    for candidate in [anchor_path.parent, *anchor_path.parents]:
        if (candidate / "templates").exists() and (candidate / "skills").exists():
            return candidate

    # py2app bundles scripts under Contents/Resources and packages under
    # Contents/Resources/lib/pythonX.Y. Walk up until the Resources root.
    parts = anchor_path.parts
    if "Resources" in parts:
        idx = parts.index("Resources")
        return Path(*parts[: idx + 1])

    return anchor_path.parent
