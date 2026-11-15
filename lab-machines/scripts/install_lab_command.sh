#!/bin/sh
# Install a `lab` command that runs the research workspace's tools/lab.py with this machine's Python.
# Usage: install_lab_command.sh <repo> <python> [bin_dir]   (bin_dir defaults to ~/.local/bin)
set -eu
REPO=$1
PY=$2
BIN=${3:-$HOME/.local/bin}
[ -f "$REPO/tools/lab.py" ] || { echo "no tools/lab.py in $REPO" >&2; exit 1; }
[ -x "$PY" ] || { echo "python not executable: $PY" >&2; exit 1; }
mkdir -p "$BIN"
if [ -e "$BIN/lab" ] && ! grep -q "installed by lab-machines" "$BIN/lab"; then
  echo "$BIN/lab already exists and was not installed by lab-machines; leaving it alone" >&2
  exit 1
fi
cat > "$BIN/lab" <<EOF
#!/bin/sh
# lab: run the research workspace's tools/lab.py on this machine (installed by lab-machines)
# Paths given as arguments are relative to the workspace root.
cd "$REPO" || exit 1
exec "$PY" tools/lab.py "\$@"
EOF
chmod +x "$BIN/lab"
echo "installed $BIN/lab -> $REPO"
