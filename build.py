"""Assumes Python 3.10+ on Windows; no third-party build dependencies."""

from pathlib import Path
import hashlib
import json
import zipfile


def build() -> Path:
    root = Path(__file__).resolve().parent
    source = root / "ui_fonts"
    version = json.loads((source / "manifest.json").read_text(encoding="utf-8"))["human_version"]
    output = root / "dist" / f"anki-ui-fonts-{version}.ankiaddon"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.iterdir()):
            if path.suffix not in {".py", ".json", ".md"} or path.name == "meta.json":
                continue
            info = zipfile.ZipInfo(path.name, date_time=(2026, 11, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
        license_info = zipfile.ZipInfo("LICENSE", date_time=(2026, 11, 7, 0, 0, 0))
        license_info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(license_info, (root / "LICENSE").read_bytes(), compresslevel=9)
    print(output)
    print("SHA256 " + hashlib.sha256(output.read_bytes()).hexdigest())
    return output


if __name__ == "__main__":
    build()
