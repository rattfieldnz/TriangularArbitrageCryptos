#!/usr/bin/env python
# coding: utf-8

# # IMPORTS

# In[1]:


import os
import ccxt
import pandas as pd
import time
from datetime import datetime
from config import myconfig
import math
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path('.env')    # Rename .env.example to .env, then update API keys as appropriate.
load_dotenv(dotenv_path=dotenv_path)


# # INITIALIZE

# In[2]:


exchange = ccxt.gate({
    "apiKey": os.getenv('API_KEY'),
    "secret": os.getenv('API_SECRET')
})


# In[3]:


markets = exchange.fetchMarkets()
market_symbols = [market['symbol'] for market in markets]
print(f'No. of market symbols: {len(market_symbols)}')
print(f'Sample:{market_symbols[0:5]}')


# # STEP 1: GET ALL THE CRYPTO COMBINATIONS FOR USDT

# In[4]:


def get_crypto_combinations(market_symbols, base):
    combinations = []
    for sym1 in market_symbols:
        
        sym1_token1 = sym1.split('/')[0]
        sym1_token2 = sym1.split('/')[1]
        
        if (sym1_token2 == base):
            for sym2 in market_symbols:
                sym2_token1 = sym2.split('/')[0]
                sym2_token2 = sym2.split('/')[1]
                if (sym1_token1 == sym2_token2):
                    for sym3 in market_symbols:
                        sym3_token1 = sym3.split('/')[0]
                        sym3_token2 = sym3.split('/')[1]
                        if((sym2_token1 == sym3_token1) and (sym3_token2 == sym1_token2)):
                            combination = {
                                'base':sym1_token2,
                                'intermediate':sym1_token1,
                                'ticker':sym2_token1,
                            }
                            combinations.append(combination)
                

    return combinations
        
wx_combinations_usdt = get_crypto_combinations(market_symbols,'USDT')


# In[5]:


print(f'No. of crypto combinations: {len(wx_combinations_usdt)}')

cominations_df = pd.DataFrame(wx_combinations_usdt)
cominations_df.head()


# # STEP 2: PERFORM TRIANGULAR ARBITRAGE

# ## Utility method to fetch the current ticker price

# In[6]:


def fetch_current_ticker_price(ticker):
    current_ticker_details = exchange.fetch_ticker(ticker)
    ticker_price = current_ticker_details['close'] if current_ticker_details is not None else None
    return ticker_price


# In[7]:


def check_if_float_zero(value):
    return math.isclose(value, 0.0, abs_tol=1e-3)


# ## Triangular Arbitrage

# In[8]:


def check_buy_buy_sell(scrip1, scrip2, scrip3,initial_investment):
    
    ## SCRIP1
    investment_amount1 = initial_investment
    current_price1 = fetch_current_ticker_price(scrip1)
    final_price = 0
    scrip_prices = {}
    
    if current_price1 is not None and not check_if_float_zero(current_price1):
        buy_quantity1 = round(investment_amount1 / current_price1, 8)
        
        # TRY WITHOUT SLEEP IF THE EXCHANGE DOES NOT THROW RATE LIMIT EXCEPTIONS
        time.sleep(1)
        ## SCRIP2
        investment_amount2 = buy_quantity1     
        current_price2 = fetch_current_ticker_price(scrip2)
        if current_price2 is not None and not check_if_float_zero(current_price2):
            buy_quantity2 = round(investment_amount2 / current_price2, 8)
            
            # TRY WITHOUT SLEEP IF THE EXCHANGE DOES NOT THROW RATE LIMIT EXCEPTIONS
            time.sleep(1)
            ## SCRIP3
            investment_amount3 = buy_quantity2     
            current_price3 = fetch_current_ticker_price(scrip3)
            if current_price3 is not None and not check_if_float_zero(current_price3):
                sell_quantity3 = buy_quantity2
                final_price = round(sell_quantity3 * current_price3,3)
                scrip_prices = {scrip1 : current_price1, scrip2 : current_price2, scrip3 : current_price3}
                
    return final_price, scrip_prices


# In[9]:


def check_buy_sell_sell(scrip1, scrip2, scrip3,initial_investment):
    ## SCRIP1
    investment_amount1 = initial_investment
    current_price1 = fetch_current_ticker_price(scrip1)
    final_price = 0
    scrip_prices = {}
    if current_price1 is not None and not check_if_float_zero(current_price1):
        buy_quantity1 = round(investment_amount1 / current_price1, 8)
        
        # TRY WITHOUT SLEEP IF THE EXCHANGE DOES NOT THROW RATE LIMIT EXCEPTIONS
        time.sleep(1)
        ## SCRIP2
        investment_amount2 = buy_quantity1     
        current_price2 = fetch_current_ticker_price(scrip2)
        if current_price2 is not None and not check_if_float_zero(current_price2):
            sell_quantity2 = buy_quantity1
            sell_price2 = round(sell_quantity2 * current_price2,8)
            
            # TRY WITHOUT SLEEP IF THE EXCHANGE DOES NOT THROW RATE LIMIT EXCEPTIONS
            time.sleep(1)
            ## SCRIP1
            investment_amount3 = sell_price2     
            current_price3 = fetch_current_ticker_price(scrip3)
            if current_price3 is not None and not check_if_float_zero(current_price3):
                sell_quantity3 = sell_price2
                final_price = round(sell_quantity3 * current_price3,3)
                scrip_prices = {scrip1 : current_price1, scrip2 : current_price2, scrip3 : current_price3}
    return final_price,scrip_prices


# In[10]:


def check_profit_loss(total_price_after_sell,initial_investment,transaction_brokerage, min_profit):
    apprx_brokerage = transaction_brokerage * initial_investment/100 * 3
    min_profitable_price = initial_investment + apprx_brokerage + min_profit
    profit_loss = round(total_price_after_sell - min_profitable_price,3)
    return profit_loss


# In[ ]:





# # STEP 3: PLACE THE TRADE ORDERS

# In[11]:


def place_buy_order(scrip, quantity, limit):
    order = exchange.create_limit_buy_order(scrip, quantity, limit)
    return order

def place_sell_order(scrip, quantity, limit):
    order = exchange.create_limit_sell_order(scrip, quantity, limit)
    return order 

def place_trade_orders(type, scrip1, scrip2, scrip3, initial_amount, scrip_prices):
    final_amount = 0.0
    if type == 'BUY_BUY_SELL':
        s1_quantity = initial_amount/scrip_prices[scrip1]
        place_buy_order(scrip1, s1_quantity, scrip_prices[scrip1])
        
        s2_quantity = s1_quantity/scrip_prices[scrip2]
        place_buy_order(scrip2, s2_quantity, scrip_prices[scrip2])
        
        s3_quantity = s2_quantity
        place_sell_order(scrip3, s3_quantity, scrip_prices[scrip3])
        
    elif type == 'BUY_SELL_SELL':
        s1_quantity = initial_amount/scrip_prices[scrip1]
        place_buy_order(scrip1, s1_quantity, scrip_prices[scrip1])
        
        s2_quantity = s1_quantity
        place_sell_order(scrip2, s2_quantity, scrip_prices[scrip2])
        
        s3_quantity = s2_quantity * scrip_prices[scrip2]
        place_sell_order(scrip3, s3_quantity, scrip_prices[scrip3])
        
        
    return final_amount


# Sample order from exchange immediately after execution:   
# {'info': {'id': '2490462375', 'symbol': 'btcusdt', 'type': 'limit', 'side': 'buy', 'status': 'wait', 'price': '43201.0', 'origQty': '0.002314', 'executedQty': '0.0', 'createdTime': '1646302254000', 'updatedTime': '1646302254000'}, 'id': '2490462375', 'clientOrderId': None, 'timestamp': 1646302254000, 'datetime': '2022-03-03T10:10:54.000Z', 'lastTradeTimestamp': 1646302254000, 'status': 'open', 'symbol': 'BTC/USDT', 'type': 'limit', 'timeInForce': None, 'postOnly': None, 'side': 'buy', 'price': 43201.0, 'amount': None, 'filled': 0.0, 'remaining': None, 'cost': 0.0, 'fee': None, 'average': None, 'trades': [], 'fees': []}

# In[ ]:





# # STEP 4: WRAPPING IT TOGETHER

# In[12]:


def perform_triangular_arbitrage(scrip1, scrip2, scrip3, arbitrage_type,initial_investment, 
                               transaction_brokerage, min_profit):
    final_price = 0.0
    if(arbitrage_type == 'BUY_BUY_SELL'):
        # Check this combination for triangular arbitrage: scrip1 - BUY, scrip2 - BUY, scrip3 - SELL
        final_price, scrip_prices = check_buy_buy_sell(scrip1, scrip2, scrip3,initial_investment)
        
    elif(arbitrage_type == 'BUY_SELL_SELL'):
        # Check this combination for triangular arbitrage: scrip1 - BUY, scrip2 - SELL, scrip3 - SELL
        final_price, scrip_prices = check_buy_sell_sell(scrip1, scrip2, scrip3,initial_investment)
        
    profit_loss = check_profit_loss(final_price,initial_investment, transaction_brokerage, min_profit)

    if profit_loss>0:
        print(f"PROFIT-{datetime.now().strftime('%H:%M:%S')}:"\
              f"{arbitrage_type}, {scrip1},{scrip2},{scrip3}, Profit/Loss: {round(final_price-initial_investment,3)} ")
        
        # UNCOMMENT THIS LINE TO PLACE THE ORDERS
        #place_trade_orders(arbitrage_type, scrip1, scrip2, scrip3, initial_investment, scrip_prices)



# In[13]:


INVESTMENT_AMOUNT_DOLLARS = 100
MIN_PROFIT_DOLLARS = 0.5
BROKERAGE_PER_TRANSACTION_PERCENT = 0.2

# UNCOMMENT THE WHILE LOOP TO RUN THIS LOOP CONTINUOUSLY
#while(1):
for combination in wx_combinations_usdt:

    base = combination['base']
    intermediate = combination['intermediate']
    ticker = combination['ticker']


    s1 = f'{intermediate}/{base}'    # Eg: BTC/USDT
    s2 = f'{ticker}/{intermediate}'  # Eg: ETH/BTC
    s3 = f'{ticker}/{base}'          # Eg: ETH/USDT 

    # Check triangular arbitrage for buy-buy-sell 
    perform_triangular_arbitrage(s1,s2,s3,'BUY_BUY_SELL',INVESTMENT_AMOUNT_DOLLARS,
                              BROKERAGE_PER_TRANSACTION_PERCENT, MIN_PROFIT_DOLLARS)
    # Sleep to avoid rate limit on api calls (RateLimitExceeded exception)
    time.sleep(1) 
    # Check triangular arbitrage for buy-sell-sell 
    perform_triangular_arbitrage(s3,s2,s1,'BUY_SELL_SELL',INVESTMENT_AMOUNT_DOLLARS,
                              BROKERAGE_PER_TRANSACTION_PERCENT, MIN_PROFIT_DOLLARS)
    time.sleep(1)    
         
    


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




