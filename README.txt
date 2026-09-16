SMART RICHARD
=============

1% BETTER EVERY DAY.

An after-market SGX swing dashboard built for Richard.

START THE DASHBOARD

1. Double-click START.command while connected to the internet.
2. SMART RICHARD refreshes its delayed market data and daily scoring inputs.
3. Safari opens automatically when the refresh finishes.
4. Keep the small Terminal window open while using the dashboard.
5. Close the Terminal window when you are finished.

If Safari ever shows an old-looking layout, close that tab and double-click
START.command again. Version 5 prevents Safari from reusing old design files.

There is nothing to install. The dashboard works locally on this Mac.


USING THE DASHBOARD

- Click a stock card to see the simple reason and trade plan.
- Read the mini chart for the stock's recent two-month daily price trend.
- BUY WATCH cards show a suggested entry zone for a possible pullback.
- Use Search to find a stock already on the watchlist.
- Click the star to mark a favourite.
- Click Edit list to move or remove stocks.
- Click Add stock to search 200 popular SGX stocks, REITs and ETFs.
- Click the moon or sun button to change between light and dark mode.

Watchlist changes and favourites are saved in this browser on this Mac.


MARKET DATA

update_scan.py downloads delayed daily prices and writes scan.json before the
dashboard opens. It uses no API key and installs nothing.

If the data service is unavailable, SMART RICHARD opens the last saved scan.
The dashboard checks every minute for a newly written scan.

Suggested entry zones appear only for BUY WATCH stocks. The zone looks for a
small pullback toward the rising 20-day trend, adjusted for that stock's recent
average daily movement. The displayed stop uses the same daily movement measure,
and the target is set at approximately twice the planned risk.


THE THREE DATA FILES

scan.json       Today's analysis and trade plans.
watchlist.json  The default order of stocks on a new browser.
stocks.json     The searchable 200-counter SGX directory.


GITHUB PAGES

Read GITHUB-HOSTING.txt for the simple publishing steps. The included GitHub
workflow refreshes the delayed scan hourly during SGX market sessions on weekdays,
then publishes the updated dashboard automatically.

IMPORTANT

Prices are delayed and the score is produced by simple rules based on daily price
direction, momentum, trading activity and the wider STI trend. It is not a promise,
personal recommendation or financial advice. Always confirm the latest price and
do your own checks before trading.
