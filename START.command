#!/bin/zsh

cd "${0:A:h}"
clear

echo "SMART RICHARD"
echo "Better every day."
echo ""
echo "Refreshing delayed market data…"
python3 update_scan.py
if [ $? -ne 0 ]; then
  echo ""
  echo "Could not reach the market-data service. Opening the last saved scan instead."
fi

echo ""
python3 server.py

echo ""
echo "You can close this window."
read -k 1 "?Press any key to finish."
