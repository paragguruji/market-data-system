# Task Description

Build a simple market data system that reads a config file at startup, and then reads commands from stdin & writes to stdout.

### Config file

Config file is in json format and consists of two keys: “symbols” and “users”. Here is an example of the config file with each object explained below:

``` 
{
  "symbols": {
    "TSLA": {
      "currency": "USD"
    },
    "BMW": {
      "currency": "EUR"
    },
    "AZN": {
      "currency": "GBP"
    },
    "GBP": {
      "currency": "USD"
    },
    "EUR": {
      "currency": "USD"
    }
  },
  "users": {
    "elon.musk": ["TSLA", "AZN", "GBP"],
    "bill.gates": ["MSFT", "TSLA", "GBP"]
  }
}
```



#### Symbols section

There are several series of data, each identified by a name, aka symbol. Symbol has currency and price. List of possible symbols with their currencies is configured in the “symbols” section of the configuration file with the schema as per example above.

We also support a set of currencies, that are configured in the same section. Their currency is always “USD” and their price represents amount of US dollars per 1 unit of currency (i.e. EUR price is how 1 EUR is in US dollars).

When the application starts, symbols have no price.

#### User Entitlements section

The system also needs to implement permissions based on user requesting data. A user can have access to some symbols, but not others. This is stored in the object under the “users” key, as per the example above.

So each user is associated with a list of symbols s/he is entitled to.



### Commands from stdin

The application should take input command from stdin (console) and process them. In the command. Commands are:

- **tick \<symbol> \<price>**\
Process symbol price event. The price is in symbol’s currency and indicates its new price.
- **subscribe \<user> \<symbol> [\<currency>]**\
Creates a subscription for the user to the specified symbol and optionally currency. If currency is omitted the symbol's own currency is assumed. The application should create a subscription if the user is entitled to the symbol. Otherwise print “User \<user> is not entitled to \<symbol>“. If there is already an existing subscription for this user to this symbol and currency print “Subscription already exists”. If currency is different to the symbol’s native currency the currency conversion should apply too. If the user is not entitled to any dependent currency error as above should be printed.
- **unsubscribe \<user> \<symbol> [\<currency>]**\
Removes subscription. If such subscription does not exist print “Subscription does not exist”
- **quit**\
Exit the application

Subscription should react to tick events of the symbol or dependent currency symbols. When started it should output initial state containing user name, symbol, subscription currency and symbol’s current price in this currency, all separated by space , e.g.

``` 
elon.musk TESLA USD 219.27
```

As relevant ticks arrive the updated price should be printed in the same format for each active subscription.

If there is no price for the symbol, or there is no price for any relevant currency, if subscription is in a different currency, price is omitted (together with the space before it).

Example of input/output:

``` 
>tick TSLA 219.27
>subscribe elon.musk TSLA
elon.musk TSLA USD 219.27
>subscribe bill.gates BMW
User bill.gates is not entitled to BMW
>subscribe bill.gates TSLA
bill.gates TSLA USD 219.27
>tick TSLA 219.5
elon.musk TSLA USD 219.5
bill.gates TSLA USD 219.5
>unsubscribe bill.gates TSLA
>subscribe bill.gates TSLA GBP
bill.gates TSLA GBP
>tick GBP 1.25
bill.gates TSLA GBP 175.6
>tick TSLA 220.5
elon.musk TSLA USD 220.5
bill.gates TSLA GBP 176.4
>quit
```

NB. Input is marked with “>” for the clarity of the example, no need to print it


# Project Structure

Structure your project as you see fit with the following exceptions:

- requirements.txt = put any Python package requirements here (remember to run Install if using Web GUI)
- src/app.py - main entry
- data/config.json - example configuration, feel free to modify


# Take Home Assessment Objective

The purpose of this exercise is NOT to find out if you can write code that runs and works perfectly, nor it is to investigate your knowledge of our chosen business area.

The test is to approach the problem as you would if you were already part of the team, working on creating a prototype for a new component of our system. One for which the requirements and constraints are still unclear, and which we hope to use as starting block for the full implementation.
