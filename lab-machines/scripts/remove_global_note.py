#!/usr/bin/env python3
"""Remove the lab-machines block that older installs wrote into a global agent instruction file.

Usage: remove_global_note.py <target>
  target  e.g. ~/.codex/AGENTS.md or ~/.claude/CLAUDE.md

The lab-machines and research-project rules apply only inside repos whose own
AGENTS.md opts in (the research-project template and the hub repo do), never
globally. Text outside the block is kept; the original is copied to <target>.bak
first. If nothing but the block was in the file, the file is removed.
Python 3.6+, standard library only.
"""
import re
import shutil
import sys
from pathlib import Path

BEGIN, END = "<!-- lab-machines:begin -->", "<!-- lab-machines:end -->"


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    target = Path(argv[1]).expanduser()
    if not target.is_file():
        print("no file", target)
        return
    text = target.read_text(encoding="utf-8")
    pattern = re.compile(r"\n*" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n*", re.S)
    if not pattern.search(text):
        print("no lab-machines block in", target)
        return
    shutil.copy2(str(target), str(target) + ".bak")
    rest = pattern.sub("\n\n", text).strip("\n")
    if rest.strip():
        target.write_text(rest + "\n", encoding="utf-8")
        print("removed block from", target, "(backup", str(target) + ".bak)")
    else:
        target.unlink()
        print("removed", target, "(it held only the block; backup", str(target) + ".bak)")


if __name__ == "__main__":
    main(sys.argv)
