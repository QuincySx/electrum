import contextlib
import time
from typing import Any, Callable

from trezorlib import customer_ui

from electrum_gui.common.basic.functional.wraps import timeout_lock
from electrum_gui.common.hardware import exceptions

AGENT = customer_ui.CustomerUI


def get_value_of_agent(attr_name: str, default=None):
    return getattr(AGENT, attr_name, default)


def set_value_to_agent(attr_name: str, value: Any):
    return setattr(AGENT, attr_name, value)


@contextlib.contextmanager
@timeout_lock("hardware_helper.require_specific_value_of_agent", timeout=60, raise_if_timeout=True)
def require_specific_value_of_agent(attr_name: str, message_code: int) -> Callable:
    set_value_to_agent("user_cancel", None)
    set_value_to_agent(attr_name, None)
    set_value_to_agent("code", str(message_code))

    def _wait_until_timeout(timeout: int = 60):
        expired_at = time.time() + timeout

        while time.time() < expired_at:
            value = get_value_of_agent(attr_name)

            if value is not None:
                return value
            elif get_value_of_agent("user_cancel") is not None:
                raise exceptions.Cancelled()
            else:
                time.sleep(0.01)

        raise exceptions.CallbackTimeout()

    try:
        yield _wait_until_timeout
    finally:
        set_value_to_agent("user_cancel", None)
        set_value_to_agent(attr_name, None)
        set_value_to_agent("code", None)
