#!/usr/bin/env bash
# Run after uploading code to the Passenger/cPanel application directory.
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_root"

# Clear only application bytecode; leave virtual environments alone.
find dental_family main_server -type f -name '*.pyc' -delete
find dental_family main_server -depth -type d -name '__pycache__' -empty -delete
mkdir -p tmp
touch tmp/restart.txt
printf 'Passenger restart requested for %s\n' "$project_root"
