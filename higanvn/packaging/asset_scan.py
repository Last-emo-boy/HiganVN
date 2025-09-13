from __future__ import annotations

"""Static asset reference scanner for .vns scripts.

Parses a .vns source (using existing parser) and extracts referenced asset names:
 - Backgrounds: > BG path
 - CG: > CG path
 - BGM: ♪ path or > BGM path
 - SE: > SE path
 - Characters & poses: dialogue actor + (emotion) -> ch/<actor>/base.png and ch/<actor>/pose_<emotion>.png

Returned structure (dict) keys:
    {
        "bg": set[str],
        "cg": set[str],
        "bgm": set[str],
        "se": set[str],
        "actors": { actor: set[emotions] }
    }

This is conservative; dynamic commands or effect tags are not interpreted as assets.
"""

from pathlib import Path
from typing import Dict, Set

from higanvn.script.parser import parse_script


def scan_script_assets(source: str) -> dict:
    program = parse_script(source)
    bg: Set[str] = set()
    cg: Set[str] = set()
    bgm: Set[str] = set()
    se: Set[str] = set()
    voice: Set[str] = set()
    actors: Dict[str, Set[str]] = {}
    for op in program.ops:
        k = op.kind
        p = op.payload
        if k == "command":
            name = (p.get("name") or "").upper()
            args = p.get("args") or ""
            parts = args.split()
            if name == "BG" and parts:
                if parts[0].lower() != "none":
                    bg.add(parts[0])
            elif name == "CG" and parts:
                if parts[0].lower() != "none":
                    cg.add(parts[0])
            elif name == "BGM" and parts:
                if parts[0].lower() != "none":
                    bgm.add(parts[0])
            elif name == "SE" and parts:
                if parts[0].lower() != "none":
                    se.add(parts[0])
            elif name == "VOICE" and parts:
                if parts[0].lower() != "none":
                    voice.add(parts[0])
        elif k == "dialogue":
            actor = p.get("actor")
            emo = p.get("emotion")
            if actor:
                if actor not in actors:
                    actors[actor] = set()
                if emo:
                    actors[actor].add(str(emo))
    return {
        "bg": bg,
        "cg": cg,
        "bgm": bgm,
        "se": se,
    "actors": actors,
    "voice": voice,
    }


def scan_script_file(path: Path) -> dict:
    src = Path(path).read_text(encoding="utf-8")
    return scan_script_assets(src)


def build_asset_manifest(script_path: Path, assets_root: Path, namespace: str | None = None) -> dict:
    """Produce a manifest with existing file resolution for referenced assets.

    namespace (script stem) lets us check namespaced folders first.
    """
    data = scan_script_file(script_path)
    base_candidates = [assets_root]
    if namespace:
        base_candidates.insert(0, assets_root / namespace)

    def resolve_list(cat: str, names: set[str]) -> list[str]:
        out: list[str] = []
        for n in sorted(names):
            found = None
            for base in base_candidates:
                p = base / cat / n
                if p.exists():
                    found = p.relative_to(assets_root).as_posix()
                    break
            out.append(found or f"MISSING:{n}")
        return out

    resolved = {
        "backgrounds": resolve_list("bg", data["bg"]),
        "cgs": resolve_list("cg", data["cg"]),
        "bgm": resolve_list("bgm", data["bgm"]),
        "se": resolve_list("se", data["se"]),
        "voice": resolve_list("voice", data.get("voice", set())),
        "characters": {},
    }
    for actor, emos in sorted(data["actors"].items()):
        actor_entry = {"base": None, "poses": {}}
        for base in base_candidates:
            base_path = base / "ch" / actor / "base.png"
            if base_path.exists():
                actor_entry["base"] = base_path.relative_to(assets_root).as_posix()
                break
        for emo in sorted(emos):
            pose_found = None
            for base in base_candidates:
                pose_path = base / "ch" / actor / f"pose_{emo}.png"
                if pose_path.exists():
                    pose_found = pose_path.relative_to(assets_root).as_posix()
                    break
            actor_entry["poses"][emo] = pose_found or f"MISSING:pose_{emo}.png"
        resolved["characters"][actor] = actor_entry
    return resolved


__all__ = [
    "scan_script_assets",
    "scan_script_file",
    "build_asset_manifest",
]