import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pixell.ui import make_patch, validate_patch_scope


def main() -> None:
    ops = [
        {"op": "replace", "path": "/data/ui/selected", "value": [1, 2, 3]},
        {"op": "add", "path": "/view/children/0/props/disabled", "value": False},
    ]
    validate_patch_scope(ops)
    patch = make_patch(ops)
    print(json.dumps({"type": "ui.patch", "patch": patch}, indent=2))


if __name__ == "__main__":
    main() 