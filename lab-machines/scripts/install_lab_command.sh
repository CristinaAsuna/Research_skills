#!/bin/sh
# Install a `lab` command that runs this skill's scripts/lab.py with the machine's Python, in the current directory.
# Usage: install_lab_command.sh <python> <hub_repo> [bin_dir]   (bin_dir defaults to ~/.local/bin)
#   <hub_repo>: the shared hub repository, used when `lab` runs outside any git repository (written to ~/.config/lab/hub)
set -eu
PY=$1
HUB=$2
BIN=${3:-$HOME/.local/bin}
HERE=$(cd "$(dirname "$0")" && pwd)
[ -f "$HERE/lab.py" ] || { echo "no lab.py next to $0" >&2; exit 1; }
[ -x "$PY" ] || { echo "python not executable: $PY" >&2; exit 1; }
[ -d "$HUB/.git" ] || { echo "hub is not a git repository: $HUB" >&2; exit 1; }
mkdir -p "$BIN" "$HOME/.config/lab"
if [ -e "$BIN/lab" ] && ! grep -q "installed by lab-machines" "$BIN/lab"; then
  echo "$BIN/lab already exists and was not installed by lab-machines; leaving it alone" >&2
  exit 1
fi
cat > "$BIN/lab" <<EOF
#!/bin/sh
# lab: shared record of what ran where (installed by lab-machines). Runs in the current directory.
exec "$PY" "$HERE/lab.py" "\$@"
EOF
chmod +x "$BIN/lab"
printf '%s\n' "$HUB" > "$HOME/.config/lab/hub"
echo "installed $BIN/lab -> $HERE/lab.py (hub: $HUB)"
