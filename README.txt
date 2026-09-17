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
- BUY WATCH cards show a suggested entry zone and rule-based exit target.
- The blue Turning up? filter finds early improvement after a downtrend.
- In Add stock, use Turning up only to discover candidates across the full scan.
- Use Search to find a stock already on the watchlist.
- Click the star to mark a favourite.
- Click Edit list to move or remove stocks.
- Click Add stock to search the active SGX share-counter directory.
- Click the moon or sun button to change between light and dark mode.

Watchlist changes and favourites are saved in this browser on this Mac.


MARKET DATA

update_scan.py downloads delayed daily prices and writes scan.json before the
dashboard opens. It uses no API key and installs nothing.

If the data service is unavailable, SMART RICHARD opens the last saved scan.
The dashboard checks every minute for a newly written scan.

Suggested entry zones and exit targets appear only for BUY WATCH stocks. The zone looks for a
small pullback toward the rising 20-day trend, adjusted for that stock's recent
average daily movement. The displayed stop uses the same daily movement measure,
and the target is set at approximately twice the planned risk.

"Possible turnaround" is deliberately separate from BUY WATCH. It looks for a
stock that was below its longer trend but now has an improving 20-day trend,
better one-week price action and recovering momentum. It is an early-warning
flag, not a prediction or confirmation that an uptrend will continue.


THE THREE DATA FILES

scan.json       Today's analysis and trade plans.
watchlist.json  The default order of stocks on a new browser.
stocks.json     The searchable active SGX share-counter directory.

refresh_universe.py rebuilds stocks.json from the SGX issuer directory and keeps
only counters with sufficiently recent price history. Run it occasionally when
new listings or delistings need to be reflected.


GITHUB PAGES

Read GITHUB-HOSTING.txt for the simple publishing steps. The included GitHub
workflow refreshes the delayed scan hourly during SGX market sessions on weekdays,
then publishes the updated dashboard automatically.

IMPORTANT

Prices are delayed and the score is produced by simple rules based on daily price
direction, momentum, trading activity and the wider STI trend. It is not a promise,
personal recommendation or financial advice. Always confirm the latest price and
do your own checks before trading.
