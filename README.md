# Stock Trading Methods Comparison

### Overview ###

Run the code in your preferred Python environment. You will need Alexander Volkovsky's Pyxirr [module](https://github.com/Anexen/pyxirr "Library Used For Calculations") installed. You can add different methods as you prefer, or delete pre-existing ones that aren't of interest. Graphs will be generated to help you visually compare the performance of each method backtested against 10 years of data. A graph of the current methods implemented is provided. An XIRR rate will also be [calculated] to help compare the method's performance against a savings account deposit.


Some things to note:
YFinance provides adjusted prices for VOO, which may cause issues. As such, I used Google Sheets to import the actual prices and converted it into a CSV that is used for all methods(except the Market Average method, which relies on making trades on data updated every hour from YFinance). If you'd prefer to use YFinance, just set `USE_CSV` to `False`. 

You can also change which stock you're looking at by changing `ticker`. 

The program does not account for dividends, but it does account for interest you might gain by holding your cash in a brokerage account using a basic compound rate of 4% annually. This interest rate can also be adjusted. 
