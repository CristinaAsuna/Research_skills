#!/usr/bin/env python3
"""Write (or refresh) the lab-machines block in a global agent instruction file.

Usage: update_global_note.py <target> <machine> <hub_repo>
  target    e.g. ~/.codex/AGENTS.md or ~/.claude/CLAUDE.md (created if missing; text outside the block is kept)
  machine   mac | pc | cluster
  hub_repo  absolute path of the hub repo on this machine
Python 3.6+, standard library only.
"""
import re
import sys
from pathlib import Path

BEGIN, END = "<!-- lab-machines:begin -->", "<!-- lab-machines:end -->"


def main(argv):
    if len(argv) != 4:
        sys.exit(__doc__)
    target, machine, hub = Path(argv[1]).expanduser(), argv[2], argv[3]
    template = (Path(__file__).resolve().parent.parent / "assets" / "global-note.md").read_text(encoding="utf-8")
    block = template.replace("{{MACHINE}}", machine).replace("{{REPO}}", hub).strip("\n")
    text = target.read_text(encoding="utf-8") if target.is_file() else ""
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        text = pattern.sub(lambda _: block, text, count=1)
    else:
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
    print("updated", target)


if __name__ == "__main__":
    main(sys.argv)
