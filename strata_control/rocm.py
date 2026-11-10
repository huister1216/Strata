"""Which ROCm this PC has, and which one an engine uses.

The same answer is needed in three places: `setup.py` records it in `engine/BUILD.json` when it compiles the HIP
engine, the Terminal reports it, and a benchmark report names it as the GPU runtime. Before this module each place read
only some of the places AMD writes the version, so a report from a Fedora (`/usr`) install or from AMD's wheels in
`.venv` said the runtime was not measured while the build next to it had used that very ROCm.

AMD writes the version in several files, and none of them is in every install:

* an install from AMD's tar or the Debian/RPM meta-packages: `<root>/.info/version`, and on ROCm 10 `<root>/core/.info/version`;
* AMD's TheRock wheels in a venv: `.../site-packages/_rocm_sdk_core/.info/version` and `_rocm_sdk_devel/.info/version`,
  and `rocm-sdk path --root` names the root the engine is built against;
* a distribution's own packages (`/usr` on Fedora): no version file and no `rocm_version.h`, only the version packed
  into `librocm-core.so.1.0.70101` (7.1.1 -> 7*10000 + 1*100 + 1);
* `include/rocm-core/rocm_version.h` with `ROCM_VERSION_MAJOR/MINOR`, which AMD's SDK carries.

Nothing here decides which ROCm to *use* for a build: that stays in `setup.py`'s `rocm_root`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SYSTEM_ROOTS = ("/opt/rocm", "/usr")        # where a system ROCm lives; $ROCM_PATH comes first
VERSION_TEXT = re.compile(r"\d+(?:\.\d+)+")


def version_text(root) -> str | None:
    """The version a ROCm install states about itself ("7.13.0"), or None when it states none."""
    root = Path(root)
    for rel in (".info/version", "core/.info/version"):
        try:
            text = (root / rel).read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            continue
        if VERSION_TEXT.fullmatch(text):
            return text
    try:                                        # AMD's SDK header; older ones carry no patch number
        text = (root / "include" / "rocm-core" / "rocm_version.h").read_text(encoding="utf-8")
        got = {k: re.search(rf"#define\s+ROCM_VERSION_{k}\s+(\d+)", text) for k in ("MAJOR", "MINOR", "PATCH")}
        if got["MAJOR"] and got["MINOR"]:
            ver = f"{int(got['MAJOR'].group(1))}.{int(got['MINOR'].group(1))}"
            patch = int(got["PATCH"].group(1)) if got["PATCH"] else 0
            return ver + (f".{patch}" if patch else "")
    except (OSError, ValueError):
        pass
    for folder in ("lib64", "lib"):             # a distribution package with no version file: the soname carries it
        for lib in sorted((root / folder).glob("librocm-core.so.*.*.*")):
            packed = re.search(r"\.so\.\d+\.\d+\.(\d+)$", lib.name)
            if packed:
                n = int(packed.group(1))
                return f"{n // 10000}.{n // 100 % 100}.{n % 100}"
    return None


def wheel_roots() -> list[Path]:
    """The ROCm roots of AMD's wheels in this venv, newest package first."""
    out = []
    for pkg in ("_rocm_sdk_devel", "_rocm_sdk_core"):
        for site in (Path(sys.prefix) / "lib", Path(sys.prefix) / "lib64", Path(sys.prefix) / "Lib"):
            out += sorted(site.glob(f"python*/site-packages/{pkg}"))
    return out


def build_roots(engine_dir) -> list[Path]:
    """The ROCm roots an engine was built and linked against, from the BUILD.json beside its exe."""
    try:
        meta = json.loads((Path(engine_dir) / "BUILD.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    out = []
    for d in meta.get("lib_dirs") or []:        # <root>/lib, or a wheel's <root>/lib
        p = Path(d)
        out += [p, p.parent]
    return out


def build_record(engine_dir) -> dict:
    """BUILD.json beside the engine exe (its `backend`, `archs`, `rocm`, ...), or {} when there is none."""
    try:
        meta = json.loads((Path(engine_dir) / "BUILD.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return meta if isinstance(meta, dict) else {}


def version(system_roots=SYSTEM_ROOTS, engine_dir=None) -> tuple[str, str] | None:
    """(version, where it came from) for the ROCm on this PC: the one `engine_dir`'s build recorded first, then the
    folders that engine loads its libraries from, then the wheels in this venv, then `system_roots` (the caller names
    those, since `$ROCM_PATH` is theirs to read). None for none. `where` is "build", "engine", "wheels" or "system",
    so a report can say which ROCm it means."""
    meta = build_record(engine_dir)
    if meta.get("rocm"):
        return str(meta["rocm"]), "build"
    if engine_dir:
        for root in build_roots(engine_dir):
            if (found := version_text(root)):
                return found, "engine"
    for root in wheel_roots():
        if (found := version_text(root)):
            return found, "wheels"
    for root in system_roots:
        if root and (found := version_text(root)):
            return found, "system"
    return None
