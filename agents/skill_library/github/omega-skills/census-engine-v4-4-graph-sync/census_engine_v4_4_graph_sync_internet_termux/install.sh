#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y || true
pkg install python -y || true
python -m census_engine --db census.sqlite init
echo "Census Engine v4.4 installed."
