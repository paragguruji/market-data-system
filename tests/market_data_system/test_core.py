from collections import defaultdict
from io import StringIO

import pytest
from pytest_mock import MockFixture

from market_data_system.core import MarketDataService
from market_data_system.entities import Config, Security, Subscription


@pytest.fixture
def ips():
    return StringIO("")


@pytest.fixture
def ops():
    return StringIO("")


@pytest.fixture
def empty_service_config():
    return Config(dict(), dict())


@pytest.fixture
def service_fixture(empty_service_config, ips, ops, string_logger, mocker: MockFixture):
    mocker.patch("market_data_system.core.get_configured_logger").return_value = string_logger
    return MarketDataService(config=empty_service_config, in_stream=ips, out_stream=ops)


@pytest.fixture
def securities_fixture():
    return {sec.symbol: sec for sec in [
        Security("NOP", "CUR1", None),
        Security("SYM", "CUR1", 123.0),
        Security("BOL", "CUR2", 123.0)
    ]}


@pytest.fixture
def subscriptions_fixture():
    return {f"{sub.user} {sub.symbol} {sub.currency}": sub for sub in [
        Subscription("user", "NOP", "CUR1"),
        Subscription("user", "SYM", "CUR1"),
        Subscription("user", "SYM", "CUR2")
    ]}


def test_run(service_fixture, ips, ops, log_stream, mocker: MockFixture):
    mock_uuid = mocker.patch("market_data_system.core.uuid.uuid4", side_effect=["u1", "u2", "u3"])
    mock_uuid.side_effect = ["u1", "u2", "u3"]
    mock_process_one = mocker.patch("market_data_system.core.MarketDataService.process_one")
    ips.write("cmd1\ncmd2\nquit\n")
    ips.seek(0)
    service_fixture.run()
    assert mock_process_one.call_count == 2
    assert log_stream.getvalue() == ('level=INFO logger=string_logger event="CHECKPOINT: Exit" command="quit" '
                                     'correlation_id="u3"\n')


def test_process_one(service_fixture, mocker: MockFixture):
    mock_proc = {
        "invalid_args": mocker.MagicMock(return_value=TypeError("args invalid")),
        "failure": mocker.MagicMock(return_value=ValueError("command failed")),
        "success": mocker.MagicMock(return_value=None)
    }
    mocker.patch.object(service_fixture, "_processors", mock_proc)
    service_fixture.process_one("")
    service_fixture.process_one("unknown 1 2")
    service_fixture.process_one("invalid_args 1 2 3")
    service_fixture.process_one("failure 1 ")
    service_fixture.process_one("success 1 2")
    assert mock_proc["invalid_args"].call_count == 1
    assert mock_proc["invalid_args"].call_args[0] == ("1", "2", "3")
    assert mock_proc["failure"].call_count == 1
    assert mock_proc["failure"].call_args[0] == ("1",)
    assert mock_proc["success"].call_count == 1
    assert mock_proc["success"].call_args[0] == ("1", "2")


def test_publish(service_fixture, ops, log_stream):
    service_fixture.publish("test message")
    assert ops.getvalue() == "test message\n"


def test_get_price(service_fixture, ips, ops, log_stream, mocker: MockFixture):
    assert service_fixture.get_price("ANY") is None
    assert log_stream.getvalue() == 'level=DEBUG logger=string_logger event="security not found" symbol="ANY"\n'
    sec = Security("SYM", "CUR", 123.0)
    mocker.patch.object(service_fixture, "_securities", {sec.symbol: sec})
    assert service_fixture.get_price("SYM") == 123.0
    sec.price = 100.2
    assert service_fixture.get_price("SYM") == 100.2
    sec.price = None
    assert service_fixture.get_price("SYM") is None


def test_get_market_notification(
        securities_fixture, subscriptions_fixture, service_fixture, ips, ops, log_stream, mocker: MockFixture
):
    mocker.patch.object(service_fixture, "_securities", securities_fixture)
    mocker.patch("market_data_system.core.MarketDataService.get_price").return_value = 10.0
    converter_patch = mocker.patch("market_data_system.core.convert_currency")
    converter_patch.return_value = 200.0

    # Act
    assert service_fixture.get_market_notification(subscriptions_fixture["user NOP CUR1"]) == "user NOP CUR1"
    assert service_fixture.get_market_notification(subscriptions_fixture["user SYM CUR1"]) == "user SYM CUR1 123.00"

    assert service_fixture.get_market_notification(subscriptions_fixture["user SYM CUR2"]) == "user SYM CUR2 200.00"
    assert converter_patch.call_count == 1
    assert converter_patch.call_args[0] == (10, 10, 123)
    assert log_stream.getvalue() == ('level=DEBUG logger=string_logger event="currency conversion" '
                                     'source_currency="CUR1" source_rate="10.0" source_value="123.0" '
                                     'target_currency="CUR2" target_rate="10.0" target_value="200.0"\n')


def test_on_tick(securities_fixture, subscriptions_fixture, service_fixture, mocker: MockFixture):
    mocker.patch.object(service_fixture, "_securities", securities_fixture)
    with pytest.raises(ValueError) as e_info:
        service_fixture.on_tick("NONEXISTENT", "12.50")
    assert e_info.value.args[0] == "Unknown symbol: NONEXISTENT"

    mock_message_gen = mocker.patch("market_data_system.core.MarketDataService.get_market_notification")
    mock_message_gen.return_value = "any text"
    mock_publish = mocker.patch("market_data_system.core.MarketDataService.publish")

    mocker.patch.object(service_fixture, "_subscriptions_by_topic", {})
    service_fixture.on_tick("SYM", "345.50")
    assert securities_fixture["SYM"].price == 345.5

    mocker.patch.object(
        service_fixture, "_subscriptions_by_topic", {"SYM": {subscriptions_fixture["user SYM CUR1"]: None}})
    service_fixture.on_tick("SYM", "456.50")
    assert securities_fixture["SYM"].price == 456.5
    assert mock_message_gen.call_count == 1
    assert mock_publish.call_count == 1

    mocker.patch.object(
        service_fixture,
        "_subscriptions_by_topic",
        {"SYM": {subscriptions_fixture["user SYM CUR1"]: None, subscriptions_fixture["user SYM CUR2"]: None}})
    service_fixture.on_tick("SYM", "1000.23")
    assert securities_fixture["SYM"].price == 1000.23
    assert mock_message_gen.call_count == 3
    assert mock_publish.call_count == 3


def test_on_subscribe(securities_fixture, subscriptions_fixture, service_fixture, mocker: MockFixture):
    mock_publish = mocker.patch("market_data_system.core.MarketDataService.publish")
    mock_publish.return_value = None
    mock_message_gen = mocker.patch("market_data_system.core.MarketDataService.get_market_notification")
    mock_message_gen.return_value = "price notification"

    mocker.patch.object(service_fixture, "_entitlements", {})
    service_fixture.on_subscribe("user", "SYM", "CUR1")
    assert mock_publish.call_count == 1
    assert mock_publish.call_args[0][0] == "User user is not entitled to SYM"

    mocker.patch.object(service_fixture, "_securities", securities_fixture)
    mocker.patch.object(service_fixture, "_entitlements", {"user": ["SYM", "CUR2"]})
    service_fixture.on_subscribe("user", "SYM", "CUR3")
    assert mock_publish.call_count == 2
    assert mock_publish.call_args[0][0] == "User user is not entitled to CUR3"

    mocker.patch.object(service_fixture, "_active_subscriptions", {subscriptions_fixture["user SYM CUR1"]})
    service_fixture.on_subscribe("user", "SYM")
    assert mock_publish.call_count == 3
    assert mock_publish.call_args[0][0] == "Subscription already exists"

    active_subs = set()
    subs_by_topic = defaultdict(dict)
    mocker.patch.object(service_fixture, "_active_subscriptions", active_subs)
    mocker.patch.object(service_fixture, "_subscriptions_by_topic", subs_by_topic)

    service_fixture.on_subscribe("user", "SYM", "CUR1")
    assert subscriptions_fixture["user SYM CUR1"] in active_subs
    assert subscriptions_fixture["user SYM CUR1"] in subs_by_topic["SYM"]
    assert mock_publish.call_count == 4
    assert mock_publish.call_args[0][0] == "price notification"

    service_fixture.on_subscribe("user", "SYM", "CUR2")
    assert subscriptions_fixture["user SYM CUR2"] in active_subs
    assert subscriptions_fixture["user SYM CUR2"] in subs_by_topic["SYM"]
    assert subscriptions_fixture["user SYM CUR2"] in subs_by_topic["CUR2"]
    assert subscriptions_fixture["user SYM CUR2"] in subs_by_topic["CUR1"]
    assert mock_publish.call_count == 5
    assert mock_publish.call_args[0][0] == "price notification"


def test_on_unsubscribe(securities_fixture, subscriptions_fixture, service_fixture, mocker: MockFixture):
    active_subs = set()
    subs_by_topic = defaultdict(dict)
    mocker.patch.object(service_fixture, "_active_subscriptions", active_subs)
    mocker.patch.object(service_fixture, "_subscriptions_by_topic", subs_by_topic)
    mocker.patch.object(service_fixture, "_securities", securities_fixture)
    mock_publish = mocker.patch("market_data_system.core.MarketDataService.publish")
    mock_publish.return_value = None

    service_fixture.on_unsubscribe("user", "SYM", "CUR1")
    assert mock_publish.call_count == 1
    assert mock_publish.call_args[0][0] == "Subscription does not exist"

    active_subs.add(subscriptions_fixture["user SYM CUR1"])
    active_subs.add(subscriptions_fixture["user SYM CUR2"])
    subs_by_topic["SYM"] = {subscriptions_fixture["user SYM CUR1"]: None, subscriptions_fixture["user SYM CUR2"]: None}
    subs_by_topic["CUR2"] = {subscriptions_fixture["user SYM CUR2"]: None}
    subs_by_topic["CUR1"] = {subscriptions_fixture["user SYM CUR2"]: None}

    service_fixture.on_unsubscribe("user", "SYM")
    assert subscriptions_fixture["user SYM CUR1"] not in subs_by_topic["SYM"]
    assert subscriptions_fixture["user SYM CUR1"] not in active_subs

    service_fixture.on_unsubscribe("user", "SYM", "CUR2")
    assert subscriptions_fixture["user SYM CUR2"] not in active_subs
    assert len(active_subs) == 0
    assert len(subs_by_topic) == 0
    assert subscriptions_fixture["user SYM CUR2"] not in subs_by_topic.get("SYM", {})
    assert subscriptions_fixture["user SYM CUR2"] not in subs_by_topic.get("CUR1", {})
    assert subscriptions_fixture["user SYM CUR2"] not in subs_by_topic.get("CUR2", {})
