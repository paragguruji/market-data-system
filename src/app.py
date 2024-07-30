#!/usr/bin/env python
"""This module is main entrypoint of the application"""
import sys

from market_data_system.core import MarketDataService
from market_data_system.helpers import load_market_data_system_config


def main():
    """
    Entrypoint to the application:
        - Load app config
        - Initialize and run MarketDataService

    """
    config_path = sys.argv[1]
    config = load_market_data_system_config(config_path)
    service = MarketDataService(config=config, in_stream=sys.stdin, out_stream=sys.stdout)
    service.run()


if __name__ == '__main__':
    main()
