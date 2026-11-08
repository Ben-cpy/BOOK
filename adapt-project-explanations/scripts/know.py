#!/usr/bin/env python3
"""Validate a compact tree containing only established understanding."""
import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile
import time

if sys.version_info < (3, 9):
    raise SystemExit("Project Cognition Map requires Python 3.9+ (Windows: py -3.9).")

EMPTY = "# 已掌握\n"


def ignore_runtime(root):
    git = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute",
                          "--git-path", "info/exclude"], capture_output=True,
                         text=True, encoding="utf-8")
    if git.returncode != 0:
        return
    exclude = Path(git.stdout.strip())
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    lines = existing.splitlines()
    for rule in ("/.know/", "/.codex/hooks.before-cognition.json", "/.codex/cognition-install.lock"):
        if rule not in lines:
            lines.append(rule)
    updated = ("\n".join(lines) + "\n").encode()
    if not exclude.exists() or exclude.read_bytes() != updated:
        atomic_write(exclude, updated)


@contextmanager
def file_lock(path):
    """An OS-owned lock: released even if the process is interrupted."""
    with Path(path).open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            if lock.seek(0, os.SEEK_END) == 0:
                lock.write(b"\0")
                lock.flush()
            deadline = time.monotonic() + 5
            while True:
                lock.seek(0)
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("cognition map is busy; retry later")
                    time.sleep(0.05)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def validate(raw):
    if len(raw) > 16384:
        raise ValueError("map exceeds 16 KiB")
    text = raw.decode("utf-8")
    if not text.endswith("\n") or any(not c.isprintable() and c != "\n" for c in text):
        raise ValueError("use printable UTF-8, LF newlines and a final newline")
    lines = text.splitlines()
    if not lines or lines[0] != "# 已掌握":
        raise ValueError("first line must be # 已掌握")
    topic = None
    path = []
    seen = set()
    topics = set()
    count = 0
    topic_count = 0
    for line in lines[1:]:
        if not line:
            continue
        if line.startswith("## "):
            if topic is not None and topic_count == 0:
                raise ValueError("empty topic")
            topic = line[3:]
            if (not 1 <= len(topic) <= 80 or topic != topic.strip() or topic in topics
                    or re.search(r"[<>\[\]|]", topic)):
                raise ValueError("invalid or duplicate topic")
            topics.add(topic)
            path = []
            topic_count = 0
            continue
        match = re.fullmatch(r"( *)- ([^<>\[\]|]+)", line)
        if topic is None or match is None:
            raise ValueError("use topic headings and plain nested bullets")
        spaces, label = match.groups()
        depth = len(spaces) // 2
        if len(spaces) % 2 or depth > len(path) or depth > 3:
            raise ValueError("use two-space indentation with an existing parent, at most four levels")
        if label != label.strip() or not 1 <= len(label) <= 80:
            raise ValueError("use a short knowledge boundary of at most 80 characters")
        path = path[:depth] + [label]
        key = (topic, *path)
        if key in seen:
            raise ValueError("duplicate boundary")
        seen.add(key)
        topic_count += 1
        count += 1
    if topic is not None and topic_count == 0:
        raise ValueError("empty topic")
    if count > 60:
        raise ValueError("map exceeds 60 boundaries")
    return text


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic_write(path, raw):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("map", type=Path)
    args = parser.parse_args()
    try:
        raw = args.map.read_bytes()
        validate(raw)
        print(digest(raw))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
