# Requirement Clarifications & Assumptions:

### 1. Modifying "data/config.json":
<br>**Question:**<br> Can I modify only data values in config but not the JSON structure/schema? or may I even modify the schema by adding
   additional configuration like *{"base_currency": "USD"}* etc.? (Since README says "example configuration - feel free to modify"")
<br>**Assumed Answer:**<br> Do NOT modify schema because evaluators may supply their own data/config.json file with same schema but more/different data

### 2. Completeness of Config Data:
<br>**Question:**<br> Will each non-USD currency appearing at jsonpath "\$.symbols.\<SYMBOL>.currency" in the config also appear as a symbol at jsonpath "\$.symbols.\<SYMBOL>"?
<br>**Assumed Answer:**<br> Make no assumptions about completeness, treat missing data per instructions for error scenarios.

### 3. Input Validation for "tick" Event:
<br>**Question:**<br> Will input symbol in *tick* event be always valid (present in the config)? if not, should the system output any error message or just quietly drop it?
<br>**Assumed Answer:**<br> Since no clear error message content is given, do not publish anything to output, but internally log the event as warning/error for later analysis.

### 4. Order of Output Lines: 
<br>**Question:**<br> When reacting to a *tick* event, if there are multiple relevant subscriptions, does the chronological order of their creation need to be honored when printing out their latest state?
<br>**Assumed Answer:**<br> Print out the subscription state in the creation-order of subscriptions. This will simplify deterministic repetitive testing.

### 5. Rounding of Price in Currency-Conversion:
<br>**Question:**<br> When converting currencies, Should the price be rounded up to 2 decimal places?
<br>**Assumed Answer:**<br> Yes. Use default rounding mode.

### 6. Output Formatting of Prices:
<br>**Question:**<br> Should prices be printed in a specific numeric format? (e.g.: always print 2 decimal places 100 as 100.00, or 123.4 as 123.40)
<br>**Assumed Answer:**<br> Yes, always print upto 2 decimal places, adding trailing zeros if necessary, but no leading zeros. 

### 7. Scenario of Subscription in Non-Native-Currency:
##### Scenario:
* Config: *$.symbols.BMW.currency = EUR* (EUR is native currency of BMW)
* Existing subscription (say, "sub1"): *"user1 BMW GBP"*
* Event (say "tick1"): *"tick EUR \<some_price>"*<br>
* Assume all entitlements are fulfilled<br>
<br>**Question:**<br> Should *sub1* react to *tick1*?
<br>**Assumed Answer:**<br> Yes, because: 
  * Change in *EUR*'s price (expressed in USD) will change the EUR-GBP conversion rate.
  * Since price of *BMW* for *sub1* is expressed in GBP, it is sensitive to EUR-GBP conversion rate.
  * Hence, price for *sub1* will change with EUR-GBP rate even if original price of BMW expressed in its native currency *EUR* is unchanged.
  * Conclusion: *sub1* must react to 
    1. tick BMW \<price>
    2. tick GBP \<price>
    3. tick EUR \<price>
  * Put formally, **any subscription with a currency not native to its symbol, must react to tick events for its symbol, its currency, and the native currency of its symbol** 

##### Corollary:
**Question:**<br>In above scenario, if *user1* is not entitled to *EUR*, should *sub1* be allowed to react to *tick EUR*?
<br><br>**Answer & Rationale:**<br>Yes. Because *sub1* is not exposing price of *EUR* (in *USD*). It is only accessing *EUR-USD* rate to compute new price of *BMW* in *GBP* and is entitled to both *BMW* in *GBP*.