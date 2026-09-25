#!/usr/bin/env bash
# HariBatti — one-time Mac setup (Apple silicon). Safe to re-run.
# Usage:  bash scripts/setup-mac.sh
set -euo pipefail

say() { printf "\n\033[1;32m==> %s\033[0m\n" "$1"; }

say "1/7 Apple command-line tools"
xcode-select -p >/dev/null 2>&1 || { xcode-select --install; echo "Finish the popup, then re-run this script."; exit 0; }

say "2/7 Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  grep -q 'brew shellenv' ~/.zprofile 2>/dev/null || echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
fi
eval "$(/opt/homebrew/bin/brew shellenv)"

say "3/7 Core tools: git, gh, node, pnpm, uv, jq, make"
brew install git gh node pnpm uv jq make

say "4/7 Python 3.12 (via uv)"
uv python install 3.12

say "5/7 Docker runtime (OrbStack)"
brew list --cask orbstack >/dev/null 2>&1 || brew install --cask orbstack
open -a OrbStack || true

say "6/7 Ollama + free local model for the dashboard copilot"
brew install ollama
brew services start ollama || true
sleep 3
ollama pull qwen2.5:7b

say "7/7 Global CLIs: vercel, eas"
pnpm setup >/dev/null 2>&1 || true
export PNPM_HOME="$HOME/Library/pnpm"; export PATH="$PNPM_HOME:$PATH"
pnpm add -g vercel eas-cli

say "Claude Code"
command -v claude >/dev/null 2>&1 || curl -fsSL https://claude.ai/install.sh | bash
grep -q '.local/bin' ~/.zshrc 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

say "Versions"
for c in git gh node pnpm uv docker ollama vercel eas claude; do
  printf "%-8s " "$c"; ($c --version 2>/dev/null | head -1) || echo "NOT FOUND (open a new Terminal and re-check)"
done
say "Done. Open a NEW Terminal window before continuing."
