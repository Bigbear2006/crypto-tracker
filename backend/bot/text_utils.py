import re


def parse_age(text: str) -> int | None:
    pattern = re.compile(r'\D*(\d+)\s*([а-яё]+)', re.I)
    match = pattern.search(text)

    if not match:
        return

    age = int(match.group(1))
    age_type = match.group(2).lower()

    if age_type in ('минута', 'минуты', 'минут'):
        return age
    if age_type in ('час', 'часа', 'часов'):
        return age * 60
    if age_type in ('день', 'дня', 'дней'):
        return age * 1440


def age_to_str(age: int | None, *, round_big: bool = False) -> str:
    if not age:
        return 'Нет'

    if age > 1440 and (round_big or age % 1440 == 0):
        return f'{age // 1440} дней'

    if age > 60 and (round_big or age % 60 == 0):
        return f'{age // 60} часов'

    return f'{age} минут'


def price_to_str(price: int | float | None) -> str:
    if not price:
        return 'Нет'
    return f'${price}'


def chunk_list(lst: list, size: int) -> list:
    return [lst[i : i + size] for i in range(0, len(lst), size)]
