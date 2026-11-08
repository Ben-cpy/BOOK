#!/usr/bin/env python3
"""Validate a Project Cognition Map or apply one checked transition."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


TITLE = "# Project Cognition Map"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.ASCII)
ROW = re.compile(r"( {0,6})- \[([^\]]+)\] (.+) <!-- ([^ ]+) \| ([^ ]+) \| (.+) -->")
DIRECT = "可直接讲"
BRIDGE = "补桥"
FRONTIER = "待厘清"
LIMITS = {
    (DIRECT, "used"): 1,
    (DIRECT, "continued"): 2,
    (BRIDGE, "repeated"): 2,
    (BRIDGE, "reopened"): 1,
    (FRONTIER, "frontier"): 1,
}
TRANSITIONS = {
    DIRECT: {"reopened"},
    BRIDGE: {"used", "continued"},
    FRONTIER: {"used", "continued", "repeated"},
}


@dataclass(frozen=True)
class Entry:
    state: str
    reason: str
    label: str
    evidence: tuple[str, ...]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def is_slug(value):
    return isinstance(value, str) and len(value) <= 48 and SLUG.fullmatch(value) is not None


def is_turn_id(value):
    return (isinstance(value, str) and value.count(":") == 1
            and all(is_slug(part) for part in value.split(":")))


def parse_entry(line):
    match = ROW.fullmatch(line)
    check(match is not None, "invalid boundary row or metadata comment")
    indent, state, label, key, reason, references = match.groups()
    check(len(indent) % 2 == 0, "indentation must use two spaces per level")
    check(is_slug(key), "invalid entry ID")
    check(is_label(label), "invalid or oversized boundary label")
    evidence = tuple(references.split(", "))
    check(len(evidence) == LIMITS.get((state, reason)), "invalid state, reason or evidence count")
    check(all(map(is_turn_id, evidence)), "invalid evidence ID")
    check(len(evidence) == len(set(evidence)), "duplicate evidence ID")
    return len(indent) // 2, key, Entry(state, reason, label, evidence)


def is_label(value):
    return 0 < len(value) <= 56 and value == value.strip() and not any(c in value for c in "<>|")


def parse_map(raw, project):
    check(len(raw) <= 16_384, "map exceeds 16 KiB")
    check(is_slug(project), "invalid project ID")
    body = raw.decode("utf-8")
    check(body.endswith("\n") and all(c.isprintable() or c == "\n" for c in body),
          "expected printable UTF-8 with LF newlines and a final newline")
    blocks = body[:-1].split("\n\n")
    check(blocks[0] == f"{TITLE}\nProject: {project}", "invalid header or project mismatch")
    entries = {}
    groups = set()
    for block in blocks[1:]:
        header, *lines = block.split("\n")
        group = header.removeprefix("## ")
        check(header.startswith("## ") and is_label(group) and group not in groups and lines,
              f"invalid, duplicate or empty group: {header!r}")
        groups.add(group)
        path = [group]
        for line in lines:
            depth, key, entry = parse_entry(line)
            check(depth < len(path), "child has no parent at the previous level")
            path = path[:depth + 1] + [key]
            check(tuple(path) not in entries, f"duplicate boundary: {'/'.join(path)}")
            entries[tuple(path)] = entry
    check(len(entries) <= 24, "map exceeds 24 boundaries")
    return entries


def turn_order(index, project):
    check(isinstance(index, dict) and index.get("project") == project,
          "user-turn index project mismatch")
    turns = index.get("user_turns")
    check(isinstance(turns, list) and all(map(is_turn_id, turns)), "invalid user-turn index")
    order = {turn: position for position, turn in enumerate(turns)}
    check(len(order) == len(turns), "duplicate turn in user-turn index")
    return order


def check_change(before, after, order):
    check(before.keys() <= after.keys(), "apply cannot remove entries")
    check(list(before) == [key for key in after if key in before], "apply cannot reorder entries")
    changed = [key for key in after if before.get(key) != after[key]]
    check(len(changed) == 1, "apply requires exactly one entry change")
    key, = changed
    old, new = before.get(key), after[key]
    if old is None:
        check(new.reason in {"repeated", "used", "frontier"}, "invalid reason for a new boundary")
        evidence = new.evidence
        if new.reason == "frontier":
            parent = before.get(key[:-1])
            check(parent is not None and parent.state == DIRECT,
                  "a new frontier requires a direct parent")
            evidence = parent.evidence + evidence
    else:
        check(new.reason in TRANSITIONS[old.state], "invalid state transition")
        check(old.label == new.label, "apply cannot rewrite the boundary label")
        evidence = old.evidence + new.evidence
        if old.state == FRONTIER and new.reason == "repeated" and old.evidence == new.evidence[:1]:
            evidence = new.evidence
    check(all(turn in order for turn in evidence), "evidence missing from the project user-turn index")
    positions = [order[turn] for turn in evidence]
    check(all(first < second for first, second in zip(positions, positions[1:])),
          "evidence must be distinct and in chronological order")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_atomically(path, raw):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as file:
            temporary = Path(file.name)
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def apply(args):
    import fcntl

    check(args.map.resolve() != args.candidate.resolve(), "candidate must be a separate file")
    proposed = args.candidate.read_bytes()
    after = parse_map(proposed, args.project)
    lock = args.map.with_name(args.map.name + ".lock")
    with lock.open("a", encoding="utf-8") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        current = args.map.read_bytes()
        before = parse_map(current, args.project)
        if current == proposed:
            return "unchanged"
        check(digest(current) == args.expected_sha256, "map changed since validation")
        order = turn_order(json.loads(args.user_turns.read_text(encoding="utf-8")), args.project)
        check_change(before, after, order)
        check(args.map.read_bytes() == current, "map changed during validation")
        replace_atomically(args.map, proposed)
    return f"updated {digest(proposed)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "apply"):
        subparser = commands.add_parser(command)
        subparser.add_argument("map", type=Path)
        subparser.add_argument("--project", required=True)
        if command == "apply":
            subparser.add_argument("--candidate", required=True, type=Path)
            subparser.add_argument("--expected-sha256", required=True)
            subparser.add_argument("--user-turns", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "apply":
            print(apply(args))
        else:
            raw = args.map.read_bytes()
            parse_map(raw, args.project)
            print(digest(raw))
    except (OSError, ValueError, ImportError) as error:
        parser.exit(1, f"know: {error}\n")


if __name__ == "__main__":
    main()
