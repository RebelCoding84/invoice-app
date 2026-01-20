from __future__ import annotations

from pathlib import Path
import zipfile


def create_backup_zip(target_zip: str, include_paths: list[str]) -> str:
    target = Path(target_zip)
    target.parent.mkdir(parents=True, exist_ok=True)
    root = Path.cwd()

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path_str in include_paths:
            path = Path(path_str)
            if not path.exists():
                print(f"Warning: backup path missing, skipped: {path}")
                continue
            if path.is_dir():
                for item in path.rglob("*"):
                    if item.is_file():
                        try:
                            arcname = item.relative_to(root)
                        except ValueError:
                            arcname = item.name
                        archive.write(item, arcname=str(arcname))
            else:
                try:
                    arcname = path.relative_to(root)
                except ValueError:
                    arcname = path.name
                archive.write(path, arcname=str(arcname))

    return str(target)
