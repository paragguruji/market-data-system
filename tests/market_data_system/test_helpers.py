import json
from io import StringIO

import pytest
from pytest_mock import MockFixture

from common.logging_adapter import KeyValContextLogger
from market_data_system.entities import Config, Security
from market_data_system.helpers import convert_currency, get_configured_logger, load_market_data_system_config


@pytest.mark.parametrize(
    "source_rate,target_rate,source_value,target_value,precision",
    [
        (1.0, 2.0, 10.0, 5.0, 2),
        (10.0, 3.0, 100.0, 333.333, 3),
        (10.0, 3.0, 100.0, 333.33333, 5),
        (3.0, 10.0, 333.33333, 100.00, 3),
        (None, 3.0, 100.0, None, 3),
        (3.0, 3.0, None, None, 3),
        (3.0, None, 2.0, None, 3)
    ]
)
def test_currency_conversion(source_rate, target_rate, source_value, target_value, precision):
    assert target_value == convert_currency(source_rate, target_rate, source_value, precision)


@pytest.fixture
def service_config():
    return {
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
            "bill.gates": ["MSFT", "TSLA", "GBP", "EUR"]
        }
    }


@pytest.fixture
def log_config():
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(message)s"
            }
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "test": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            }
        }
    }


def test_load_service_config(service_config, mocker: MockFixture):
    service_config_text = json.dumps(service_config)
    mocker.patch("builtins.open").return_value = StringIO(service_config_text)
    actual = load_market_data_system_config("anypath")
    assert isinstance(actual, Config)
    assert actual.base_currency == "USD"
    assert actual.entitlements == {k: set(v) for k, v in service_config["users"].items()}
    assert actual.securities == {k: Security(k, v["currency"]) for k, v in service_config["symbols"].items()}


def test_get_configured_logger_failure(log_config, mocker: MockFixture):
    log_config_text = json.dumps(log_config)
    mocker.patch("builtins.open").return_value = StringIO(log_config_text)
    with pytest.raises(ValueError) as e_info:
        get_configured_logger("any_logger", "any/path.json")
    assert e_info.value.args[0] == 'Logger not configured in any/path.json: any_logger'


def test_get_configured_logger_success(log_config, mocker: MockFixture):
    log_config_text = json.dumps(log_config)
    mocker.patch("builtins.open").return_value = StringIO(log_config_text)
    config_patch = mocker.patch("market_data_system.helpers.logging.config.dictConfig")
    logger_patch = mocker.patch("market_data_system.helpers.logging.getLogger")
    logger_patch.return_value = mocker.MagicMock()

    logger_name = list(log_config["loggers"].keys())[0]
    actual = get_configured_logger(logger_name, "any/path.json")
    assert config_patch.called
    assert config_patch.call_args[0][0] == log_config
    assert isinstance(actual, KeyValContextLogger)
    assert actual.logger is logger_patch.return_value
