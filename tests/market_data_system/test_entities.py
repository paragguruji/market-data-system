import typing
from dataclasses import FrozenInstanceError

import pytest

from market_data_system.entities import Security, Subscription


def test_subscription_hashable():
    obj1 = Subscription("user", "SYM", "CUR")
    assert isinstance(obj1, typing.Hashable)
    obj2 = Subscription("user", "SYM", "CUR")
    assert obj1 == obj2
    assert hash(obj1) == hash(obj2)


def test_subscription_immutable():
    obj = Subscription("user", "SYM", "CUR")
    with pytest.raises(FrozenInstanceError) as e_info1:
        obj.__setattr__("user", "new_value")
    assert e_info1.value.args[0] == "cannot assign to field 'user'"
    with pytest.raises(FrozenInstanceError) as e_info2:
        obj.__setattr__("symbol", "new_value")
    assert e_info2.value.args[0] == "cannot assign to field 'symbol'"
    with pytest.raises(FrozenInstanceError) as e_info3:
        obj.__setattr__("currency", "new_value")
    assert e_info3.value.args[0] == "cannot assign to field 'currency'"


def test_security_mutable_unhashable():
    obj1 = Security("SYM", "CUR")
    assert not isinstance(obj1, typing.Hashable)
    assert obj1.price is None
    obj1.price = 100.0
    assert obj1.price == 100.0
    obj2 = Security("SYM", "CUR", 200)
    assert obj1 != obj2
