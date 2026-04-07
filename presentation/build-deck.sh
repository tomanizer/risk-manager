#!/usr/bin/env bash
# Merge chapter markdown files into a single Marp deck (YAML front matter only in 01).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
{
  cat 01-intro-and-objectives.md
  printf '\n---\n\n'
  cat 02-run-the-bank.md
  printf '\n---\n\n'
  cat 03-change-the-bank.md
  printf '\n---\n\n'
  cat 04-risk-analytics-prd-and-references.md
} > deck.md
echo "Wrote $(pwd)/deck.md"
