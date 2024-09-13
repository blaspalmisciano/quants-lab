import os
import sys
import pandas as pd
import asyncio

# root_path = os.path.abspath(os.path.join(os.getcwd(), '../..'))
# sys.path.append(root_path)

import time
from core.data_sources import CLOBDataSource
from core.data_structures.candles import Candles
from research_notebooks.xtreet_bb.utils import read_yaml_to_dict
from core.data_sources.trades_feed.connectors.binance_perpetual import BinancePerpetualTradesFeed

class BinancePerpetualTradesFeedFallismo(BinancePerpetualTradesFeed):
    async def _get_historical_trades(self, trading_pair: str, start_time = None, end_time = None, from_id = None):
        end_ts = time.time()
        all_trades_collected = False
        all_trades = []
        ex_trading_pair = self.get_exchange_trading_pair(trading_pair)
        if from_id:
            while not all_trades_collected:
                await self._enforce_rate_limit()  # Enforce rate limit before making a request

                params = {
                    "symbol": ex_trading_pair,
                    "limit": 1000,
                    "fromId": int(from_id)
                }
                
                trades = await self._get_historical_trades_request(params)

                if trades:
                    last_timestamp = trades[-1]["T"] / 1e3
                    print(f"Fetching trades from {pd.to_datetime(last_timestamp, unit='s')}")
                    all_trades.extend(trades)
                    all_trades_collected = last_timestamp >= end_ts
                    from_id = trades[-1]["a"]
                else:
                    all_trades_collected = True

            df = pd.DataFrame(all_trades)
            df.rename(columns={"T": "timestamp", "p": "price", "q": "volume", "m": "sell_taker", "a": "id"}, inplace=True)
            df.drop(columns=["f", "l"], inplace=True)
            df["timestamp"] = df["timestamp"] / 1000
            df.index = pd.to_datetime(df["timestamp"], unit="s")
            df["price"] = df["price"].astype(float)
            df["volume"] = df["volume"].astype(float)
            return df

async def main():
    clob = CLOBDataSource()
    fallismo = BinancePerpetualTradesFeedFallismo()

    # base_path = os.path.join(root_path, "research_notebooks", "xtreet_bb", "configs")
    trading_pairs = ["TURBO-USDT"]
    # for config_path in os.listdir(base_path):
    #     if config_path != ".gitignore":
    #         config_dict = read_yaml_to_dict(os.path.join(base_path, config_path))
    #         trading_pairs.append(config_dict["trading_pair"])
    # trading_pairs = list(set(trading_pairs))
    # trading_pairs = [trading_pair for trading_pair in trading_pairs if trading_pair not in ["BANANA-USDT"]]
    DAYS_TO_DOWNLOAD = 7
    candles_dict = {}
    i = 0
    for trading_pair in trading_pairs:
        i += 1
        print(f"Fetching trades for {trading_pair} [{i} from {len(trading_pairs)}]")
        # base = pd.read_csv(f"data/candles/candles/binance_perpetual|{trading_pair}|1s.csv")
        # first_trade_id = base['first_trade_id'].max()
        base = pd.DataFrame()
        first_trade_id = 18681112
        print(f"EL ID ES {first_trade_id}")
        # base = base[base['first_trade_id'] < first_trade_id]
        trades = await fallismo._get_historical_trades(trading_pair, from_id=first_trade_id)
        pandas_interval = clob.convert_interval_to_pandas_freq("1s")
        candles_df = trades.resample(pandas_interval).agg({"price": "ohlc", "volume": "sum", 'id':'first'}).ffill()
        candles_df.columns = candles_df.columns.droplevel(0)
        candles_df.rename(columns = {'id':'first_trade_id'}, inplace = True)
        candles_df["timestamp"] = pd.to_numeric(candles_df.index) // 1e9

        # clob.dump_candles_cache(os.path.join(root_path, "data", "candles"))
        candles_df.to_csv(f"data/candles/candles/binance_perpetual|{trading_pair}|1s_trades.csv")

if __name__ == "__main__":
    asyncio.run(main())
