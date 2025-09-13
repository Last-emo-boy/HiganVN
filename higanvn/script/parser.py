from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple
import textwrap

from .model import Op, Program


DIALOGUE_QUOTE_RE = re.compile(r"[\u300c\u201c](.*?)[\u300d\u201d]$")


def _strip_comments(line: str) -> str:
    # Remove trailing comments starting with #, but not inside quotes
    in_quote = False
    buf: List[str] = []
    for ch in line:
        if ch in ('"', '“', '”', '「', '」'):
            in_quote = not in_quote
        if ch == '#' and not in_quote:
            break
        buf.append(ch)
    return ''.join(buf).rstrip()


def parse_script(source: str) -> Program:
    ops: List[Op] = []
    labels: Dict[str, int] = {}
    lines = source.splitlines()
    i = 0

    while i < len(lines):
        idx = i
        raw = lines[i]
        line = _strip_comments(raw).rstrip()
        stripped = line.lstrip()
        if not stripped:
            i += 1
            continue
        # Priority: command > label/choice > dialogue > narration
        # BGM shorthand: ♪ <path|None> [volume]
        if stripped.startswith('♪'):
            body = stripped[1:].strip()
            # allow Chinese or English quotes to encapsulate the name/path
            if (body.startswith('「') and body.endswith('」')) or (body.startswith('“') and body.endswith('”')):
                body = body[1:-1].strip()
            ops.append(Op("command", {"name": "BGM", "args": body, "line": idx + 1}))
            i += 1
            continue
        if stripped.startswith('>'):
            body = stripped[1:].strip()
            if not body:
                i += 1
                continue
            name, *rest = body.split(None, 1)
            args = rest[0] if rest else ""
            # Multiline SCRIPT block support:
            if name.upper() == 'SCRIPT' and args.strip() == '':
                # consume following indented block lines until blank or next non-indented directive
                block: List[str] = []
                j = i + 1
                while j < len(lines):
                    raw2 = lines[j]
                    # stop at next directive/label/choice or empty line without indentation
                    if raw2.lstrip().startswith(('>', '*', '?')):
                        break
                    # accept indented or empty lines as part of block
                    if raw2.strip() == '' or raw2.startswith((' ', '\t')):
                        # Keep original indentation; we'll dedent the whole block afterwards
                        block.append(raw2)
                        j += 1
                        continue
                    # non-indented non-empty -> stop
                    break
                # Dedent the collected block so top-level starts at column 0 while preserving inner structure
                script_code = textwrap.dedent("\n".join(block)).strip("\n")
                if script_code:
                    ops.append(Op("script", {"code": script_code, "line": idx + 1}))
                i = j
                continue
            # Inline SCRIPT
            if name.upper() == 'SCRIPT':
                ops.append(Op("script", {"code": args, "line": idx + 1}))
                i += 1
                continue
            ops.append(Op("command", {"name": name, "args": args, "line": idx + 1}))
            i += 1
            continue
        if stripped.startswith('*'):
            label = stripped[1:].strip()
            labels[label] = len(ops)
            ops.append(Op("label", {"name": label, "line": idx + 1}))
            i += 1
            continue
        if stripped.startswith('?'):
            # ? text -> target
            try:
                q, arrow = stripped[1:].split('->', 1)
            except ValueError:
                ops.append(Op("narration", {"text": stripped, "line": idx + 1}))
            else:
                text = q.strip()
                target = arrow.strip()
                ops.append(Op("choice", {"text": text, "target": target, "line": idx + 1}))
            i += 1
            continue
        # Force narration: leading ':' means narration; remove the ':' from displayed text
        if stripped.startswith(':'):
            ops.append(Op("narration", {"text": stripped[1:].strip(), "line": idx + 1}))
            i += 1
            continue
        # Dialogue: Actor [| alias] [(emotion)] [[effect]] : or quoted content
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            left, right = parts
            # Try quoted
            m = DIALOGUE_QUOTE_RE.search(right)
            if m:
                text = m.group(1)
                actor, alias, emotion, effect = _parse_actor_left(left)
                ops.append(Op("dialogue", {
                    "actor": actor,
                    "alias": alias,
                    "emotion": emotion,
                    "effect": effect,
                    "text": text,
                    "line": idx + 1,
                }))
                i += 1
                continue
            # Try colon form: Actor: text OR narration with leading ':'
            if left == ':' or right.startswith(':') or ':' in stripped:
                # Narration forced with ':' or general narration fallback
                if ':' in stripped:
                    # Actor: text
                    a, t = stripped.split(':', 1)
                    actor, alias, emotion, effect = _parse_actor_left(a.strip())
                    ops.append(Op("dialogue", {
                        "actor": actor,
                        "alias": alias,
                        "emotion": emotion,
                        "effect": effect,
                        "text": t.strip(),
                        "line": idx + 1,
                    }))
                else:
                    ops.append(Op("narration", {"text": stripped, "line": idx + 1}))
                i += 1
                continue
        # Fallback narration
        ops.append(Op("narration", {"text": stripped, "line": idx + 1}))
        i += 1

    return Program(ops, labels)


def _parse_actor_left(s: str) -> Tuple[str, str | None, str | None, str | None]:
    # "张鹏|学长(happy)[gray]" -> actor, alias, emotion, effect
    alias = None
    emotion = None
    effect = None
    rest = s
    # alias
    if '|' in rest:
        a, b = rest.split('|', 1)
        actor = a.strip()
        rest = b.strip()
        alias = rest
    else:
        # actor may include parentheses; we'll parse those next
        actor = rest
    # emotion
    m = re.search(r"\(([^)]+)\)", s)
    if m:
        emotion = m.group(1).strip()
    # effect
    m2 = re.search(r"\[([^\]]+)\]", s)
    if m2:
        effect = m2.group(1).strip()
    # Clean actor of decorations
    actor = re.sub(r"(\|.*)$", "", actor)
    actor = re.sub(r"\(.*\)", "", actor)
    actor = re.sub(r"\[.*\]", "", actor)
    actor = actor.strip()
    return actor, alias, emotion, effect
