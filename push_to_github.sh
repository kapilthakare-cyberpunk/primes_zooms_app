#!/bin/bash
# Auto-commit and push pricing_bands.csv to GitHub
# Usage: ./push_to_github.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV_FILE="$SCRIPT_DIR/pricing_bands.csv"

# Check if file exists
if [ ! -f "$CSV_FILE" ]; then
    echo "✗ pricing_bands.csv not found"
    exit 1
fi

# Check if there are changes to commit
cd "$SCRIPT_DIR"
if git diff --quiet pricing_bands.csv 2>/dev/null && git diff --cached --quiet pricing_bands.csv 2>/dev/null; then
    echo "ℹ No changes to pricing_bands.csv"
    exit 0
fi

# Stage, commit, and push
DATE=$(date +"%Y-%m-%d %H:%M")
git add pricing_bands.csv
git commit -m "Update pricing bands - $DATE"
git push origin main

echo "✓ Pushed to GitHub successfully"
