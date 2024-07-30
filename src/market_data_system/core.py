"""This module contains the class MarketDataService which implements core logic for Market Data System"""

import uuid
from collections import defaultdict
from typing import Callable, DefaultDict, Dict, Optional, Set, TextIO

from market_data_system.entities import Config, Security, Subscription
from market_data_system.helpers import convert_currency, get_configured_logger


class MarketDataService:
    """
    A Service that:
        - Maintains the state of Market Data System
        - Processes market data events coming from input stream and publishes resulting updates to output stream

    MarketDataService state consists of:
        :in_stream: TextIO: text stream to read input commands from
        :out_stream: TextIO: text stream to write resulting output to
        :_base_currency: str: base currency used to express currency exchange rates
        :_entitlements: Dict[str, Set[str]]: a mapping from user to set of symbols they are entitled to
        :_securities: Dict[str, Security]: a mapping from symbol to Security instance it represents
        :_active_subscriptions: Set[Subscription]: set of currently active subscriptions
        :_subscriptions_by_topic: Dict[str, Dict[Subscription, None]]: a mapping from symbol to an ordered set of
            subscriptions subscribing to its updates
        :_processors: Dict[str, Callable[..., None]]: a mapping from command word to its respective processor method
    """

    def __init__(self, config: Config, in_stream: TextIO, out_stream: TextIO):
        """
        Initializes MarketDataService based on given configuration.

        :param config: Config: Service Configuration
        :param in_stream: TextIO: text input stream
        :param out_stream: TextIO: text output stream

        """
        self.logger = get_configured_logger(self.__class__.__name__)
        self.in_stream = in_stream
        self.out_stream = out_stream
        self._base_currency = config.base_currency
        self._entitlements = config.entitlements
        self._securities = config.securities
        self._securities[self._base_currency] = Security(
            symbol=self._base_currency, currency=self._base_currency, price=1.0)
        self._active_subscriptions: Set[Subscription] = set()
        self._subscriptions_by_topic: DefaultDict[str, Dict[Subscription, None]] = defaultdict(dict)
        self._processors: Dict[str, Callable[..., None]] = {
            "tick": self.on_tick,
            "subscribe": self.on_subscribe,
            "unsubscribe": self.on_unsubscribe
        }

    def run(self) -> None:
        """
        Keep listening to input commands and process them in order `quit` command is received.
        For each command, set a new UUID as correlation id into the log-context

        """
        while True:
            self.logger.extra = dict(correlation_id=str(uuid.uuid4()))
            command = self.in_stream.readline().strip()
            if command == "quit":
                self.logger.info("CHECKPOINT: Exit", command=command)
                break
            self.process_one(command)

    def process_one(self, command: str) -> None:
        """
        Process a single command with error handling

        :param command: str: command to process

        """
        try:
            self.logger.info("CHECKPOINT: start processing command", command=command)
            parts = command.split()
            cmd, args = parts[0], parts[1:]
            self._processors[cmd](*args)
        except IndexError:
            self.logger.warning("blank command", valid=list(self._processors.keys()), command=command)
        except KeyError:
            self.logger.error("unknown command", valid=list(self._processors.keys()), command=command)
        except TypeError:
            self.logger.error("invalid args", command=command)
        except ValueError:
            self.logger.error("command failed", command=command)
        finally:
            self.logger.info("CHECKPOINT: end processing command", command=command)

    def on_tick(self, symbol: str, price: str) -> None:
        """
        Process `tick` command:
            - update price if symbol is valid
            - publish price notification to all relevant subscriptions listening on the symbol
            - NOTE: price notification is published even if incoming price is same as the existing price

        :param symbol: str: symbol in tick
        :param price: str: a string representing price in the tick event

        """
        try:
            old_price = self._securities[symbol].price
            new_price = float(price)
            self._securities[symbol].price = new_price
            self.logger.info("updated price by tick", symbol=symbol, old=old_price, new=new_price)
        except KeyError as e:
            raise ValueError(f"Unknown symbol: {symbol}") from e
        subscriptions = self._subscriptions_by_topic.get(symbol, {})
        self.logger.info("publishing tick update", symbol=symbol, subscription_count=len(subscriptions))
        for cnt, subscription in enumerate(subscriptions, start=1):
            message = self.get_market_notification(subscription=subscription)
            self.publish(message)
            self.logger.debug("published tick update", count=f"{cnt}/{len(subscriptions)}", content=message)
        self.logger.info("published tick update", symbol=symbol, subscription_count=len(subscriptions))

    def on_subscribe(self, user: str, symbol: str, currency: Optional[str] = None) -> None:
        """
        Process `subscribe` command:
            - Create a new subscription if it doesn't exist and if user has required entitlements
            - Publish initial state of new subscription or appropriate error message if unable to create subscription
            - Entitlement for symbol is always required
            - Entitlement for currency is required only if the currency is not the native currency of requested symbol

        :param user: str: subscriber user
        :param symbol: str: symbol to subscribe to the price updates of
        :param currency: Optional[str]:  (Default value = None) currency to express price updates when publishing
            to this subscription. Assume native currency of the symbol when currency is None

        """
        user_entitlements = self._entitlements.get(user, {})
        if symbol not in user_entitlements:
            self.logger.info("missing entitlement to security", user=user, symbol=symbol)
            self.publish(f"User {user} is not entitled to {symbol}")
            return

        native_currency = self._securities[symbol].currency
        subscription_currency = native_currency if currency is None else currency

        if subscription_currency != native_currency and subscription_currency not in user_entitlements:
            self.logger.info("missing entitlement to dependent currency", user=user, symbol=subscription_currency)
            self.publish(f"User {user} is not entitled to {subscription_currency}")
            return

        subscription = Subscription(user, symbol, subscription_currency)
        if subscription in self._active_subscriptions:
            self.logger.info("subscription already exists", subscription=f"{user} {symbol} {subscription_currency}")
            self.publish("Subscription already exists")
            return

        self._active_subscriptions.add(subscription)
        self.logger.debug("subscription created", subscription=f"{user} {symbol} {subscription_currency}")

        self._subscriptions_by_topic[subscription.symbol].setdefault(subscription)
        self.logger.debug("subscribed to security", user=user, security=subscription.symbol)

        if subscription.currency != native_currency:
            self._subscriptions_by_topic[subscription.currency].setdefault(subscription)
            self._subscriptions_by_topic[native_currency].setdefault(subscription)
            self.logger.debug(
                "subscription currency is not native currency of subscription security, subscribe to both",
                user=user, security=symbol, native=native_currency, dependent=subscription_currency)
        notification = self.get_market_notification(subscription=subscription)
        self.publish(notification)
        self.logger.info("published subscription update", content=notification)

    def on_unsubscribe(self, user: str, symbol: str, currency: Optional[str] = None) -> None:
        """
        Process `unsubscribe` command:
            - Remove an existing subscription from state or publish an appropriate error message if it does not exist

        :param user: str: subscriber user
        :param symbol: str: symbol to subscribe price updates of
        :param currency: Optional[str]:  (Default value = None) currency to express price updates when publishing
            to this subscription. Assume native currency of the symbol when currency is None

        """
        security = self._securities[symbol]
        if currency is None:
            currency = security.currency
            self.logger.debug("assume native currency of security since currency not provided",
                              user=user, security=symbol, native=currency)
        subscription = Subscription(user, symbol, currency)
        if subscription in self._active_subscriptions:
            for topic in [subscription.symbol, subscription.currency, security.currency]:
                # pop from all possible topics. if link does not exist, then noop
                # this simplifies implementation by avoiding checking native/non-native currencies
                self._subscriptions_by_topic[topic].pop(subscription, None)
                if len(self._subscriptions_by_topic[topic]) == 0:
                    # if no subscriptions left in this topic, clean up
                    self._subscriptions_by_topic.pop(topic)
            self.logger.debug("unlinked subscription from relevant topics",
                              subscription=f"{user} {symbol} {currency}",
                              topics=f"[{subscription.symbol}, {subscription.currency}, {security.currency}]")
            self._active_subscriptions.remove(subscription)
            self.logger.info("removed subscription", subscription=f"{user} {symbol} {currency}")
        else:
            self.publish("Subscription does not exist")
            self.logger.info("subscription does not exist", user=user, security=symbol, currency=currency)

    def get_market_notification(self, subscription: Subscription) -> str:
        """
        Generate a notification to publish for given subscription, including price conversion, if any required
            - notification format: "<USER> <SYMBOL> <CURRENCY> <PRICE>"
            - USER, SYMBOL, CURRENCY : constituents of given subscription
            - PRICE : price of SYMBOL expressed in CURRENCY

        :param subscription: Subscription: subscription to generate notification for

        """
        security = self._securities[subscription.symbol]
        price = security.price
        if price is not None and security.currency != subscription.currency:
            source_rate = self.get_price(security.currency)
            target_rate = self.get_price(subscription.currency)
            price = convert_currency(source_rate, target_rate, price)
            self.logger.debug("currency conversion",
                              source_currency=security.currency, source_rate=source_rate, source_value=security.price,
                              target_currency=subscription.currency, target_rate=target_rate, target_value=price)
        parts = [subscription.user, subscription.symbol, subscription.currency]
        if price is not None:
            parts.append(f"{price:.2f}")
        return " ".join(parts)

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Return latest price of given symbol if available.
        Return None if symbol does not exist or price is not available

        :param symbol: str: symbol to get price for

        """
        try:
            return self._securities[symbol].price
        except KeyError:
            self.logger.debug("security not found", symbol=symbol)
            return None

    def publish(self, message: str):
        """
        Write given message to the output stream of this service instance

        :param message: str: text to publish

        """
        print(message, file=self.out_stream)
