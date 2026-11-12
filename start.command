#!/bin/bash
cd "$HOME/odysseus" || exit 1
./start-macos.sh
echo
echo "Odysseus stopped. Press Return to close this window."
read
