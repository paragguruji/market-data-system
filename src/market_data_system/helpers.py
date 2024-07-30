"""This module holds helper functions for Market Data System"""

import json
import logging
import logging.config
from typing import Optional

from common.logging_adapter import KeyValContextLogger
from market_data_system.entities import Config, Security


def convert_currency(
        source_rate: Optional[float],
        target_rate: Optional[float],
        source_value: Optional[float],
        precision=2
) -> Optional[float]:
    """
    Convert from source currency to target currency given conversion rates for both w.r.t. a common base currency

    :param source_rate: Optional[float]: rate of source currency w.r.t. common base currency
    :param target_rate: Optional[float]: rate of target currency w.r.t. common base currency
    :param source_value: Optional[float]: value in source currency
    :param precision:  (Default value = 2) rounding precision
    :returns: Optional[float]: equivalent value in target currency if all params are non-null else None

    """
    if any(val is None for val in [source_rate, target_rate, source_value]):
        return None
    return round((source_value * source_rate / target_rate), precision)


def load_market_data_system_config(config_path: str) -> Config:
    """
    Load config for market data system from given JSON file

    :param config_path: str: path to config JSON file
    :returns: Instance of Config

    """
    with open(config_path, encoding='utf-8') as fp:
        config_json = json.load(fp)
    securities = {}
    entitlements = {}
    for symbol, currency_obj in config_json["symbols"].items():
        currency = currency_obj["currency"]
        securities[symbol] = Security(symbol=symbol, currency=currency)
    for user, symbols in config_json["users"].items():
        entitlements[user] = set(symbols)
    return Config(securities=securities, entitlements=entitlements)


def get_configured_logger(name: str, config_path: str = "config/logging_dict_config.json") -> KeyValContextLogger:
    """
    Create a KeyValContextLogger instance using given logger if configured in dict config JSON file

    :param name: str: name of logger in dict config
    :param config_path: str: path to JSON file containing dict config
    :returns: Instance of KeyValContextLogger
    :raises: ValueError: if given logger name is not configured in logging dict config

    """
    with open(config_path, encoding='utf-8') as fp:
        config_json = json.load(fp)
    if name not in config_json["loggers"]:
        raise ValueError(f"Logger not configured in {config_path}: {name}")
    logging.config.dictConfig(config_json)
    return KeyValContextLogger(logger=logging.getLogger(name))
