from collections.abc import Callable
from typing import Any

from aiogram.types import Message


def parse_message(
    msg: Message,
    *,
    parse_func: Callable[[str], Any],
    exceptions=(ValueError,),
) -> Any:
    try:
        value = parse_func(msg.text)
        return value
    except exceptions:
        return
