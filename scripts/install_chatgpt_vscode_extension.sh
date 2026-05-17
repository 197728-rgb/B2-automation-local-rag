#!/usr/bin/env bash
set -euo pipefail

EXTENSION_ID="openai.chatgpt"

if command -v code >/dev/null 2>&1; then
  CLI="code"
elif command -v code-insiders >/dev/null 2>&1; then
  CLI="code-insiders"
elif command -v codium >/dev/null 2>&1; then
  CLI="codium"
elif command -v code-server >/dev/null 2>&1; then
  CLI="code-server"
else
  cat >&2 <<'MSG'
No VS Code-compatible CLI was found.

Install Visual Studio Code and ensure one of these commands is in PATH:
  - code
  - code-insiders
  - codium
  - code-server

Then run:
  code --install-extension openai.chatgpt
MSG
  exit 127
fi

"$CLI" --install-extension "$EXTENSION_ID"
echo "Installed $EXTENSION_ID using $CLI"
