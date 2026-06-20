import json
import logging
import re
from datetime import datetime
from itertools import groupby
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def cashback_categories(data: List[Dict[str, Any]], year: int, month: int) -> str:
    """
    Возвращает JSON с суммами кешбэка по топ-3 категориям за указанный месяц.
    """
    logger.info(f"Старт cashback_categories: year={year}, month={month}")

    # Функция для проверки соответствия даты
    def date_matches(transaction: Dict) -> bool:
        try:
            dt = datetime.strptime(transaction["Дата операции"], "%Y-%m-%d")
            return dt.year == year and dt.month == month
        except (ValueError, KeyError):
            return False

    # Оставляем только нужные транзакции
    filtered = list(filter(date_matches, data))
    if not filtered:
        logger.warning("Нет транзакций за указанный период")
        return json.dumps({}, ensure_ascii=False)

    # Сортируем по категории для groupby
    sorted_data = sorted(filtered, key=lambda x: x.get("Категория", ""))

    # Группируем и суммируем кешбэк
    categories = {}
    for cat, group in groupby(sorted_data, key=lambda x: x.get("Категория", "")):
        total_cashback = sum(map(lambda t: float(t.get("Кешбэк", 0)), group))
        categories[cat] = int(total_cashback)

    # Сортируем по убыванию и берём топ-3
    top_categories = dict(sorted(categories.items(), key=lambda item: item[1], reverse=True)[:3])

    logger.info(f"Результат cashback_categories: {top_categories}")
    return json.dumps(top_categories, ensure_ascii=False)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Рассчитывает сумму, которую можно отложить в «Инвесткопилку» за указанный месяц.
    """
    logger.info(f"Старт investment_bank: month={month}, limit={limit}")

    # Парсим месяц (YYYY-MM)
    target_year, target_month = map(int, month.split("-"))

    def from_target_month(t: Dict) -> bool:
        try:
            dt = datetime.strptime(t["Дата операции"], "%Y-%m-%d")
            return dt.year == target_year and dt.month == target_month
        except (ValueError, KeyError):
            return False

    # Функция округления вверх до кратного limit
    def round_up(amount: float) -> float:
        return ((amount + limit - 1) // limit) * limit

    # Фильтруем и суммируем разницу
    total = sum(
        map(
            lambda t: round_up(float(t["Сумма операции"])) - float(t["Сумма операции"]),
            filter(from_target_month, transactions),
        )
    )

    logger.info(f"Итоговая сумма для «Инвесткопилки»: {total}")
    return round(total, 2)


def simple_search(data: List[Dict[str, Any]], query: str) -> str:
    """
    Возвращает JSON со всеми транзакциями, содержащими подстроку в описании или категории.
    """
    logger.info(f"Старт simple_search: query='{query}'")
    query_lower = query.lower()

    def matches(transaction: Dict) -> bool:
        desc = str(transaction.get("Описание", "")).lower()
        cat = str(transaction.get("Категория", "")).lower()
        return query_lower in desc or query_lower in cat

    result = list(filter(matches, data))
    logger.info(f"Найдено транзакций: {len(result)}")
    return json.dumps(result, ensure_ascii=False, default=str)


def phone_search(data: List[Dict[str, Any]]) -> str:
    logger.info("Старт phone_search")
    # Поддерживает +7/8, опциональные скобки, дефисы/пробелы и группы 2-3 цифры
    phone_regex = re.compile(r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{2,3}[\s\-]?\d{2,3}[\s\-]?\d{2}")

    def has_phone(transaction: Dict) -> bool:
        desc = str(transaction.get("Описание", ""))
        return bool(phone_regex.search(desc))

    result = list(filter(has_phone, data))
    logger.info(f"Найдено транзакций с телефонами: {len(result)}")
    return json.dumps(result, ensure_ascii=False, default=str)


def transfer_search(data: List[Dict[str, Any]]) -> str:
    """
    Возвращает JSON с переводами физическим лицам.
    Условие: категория == 'Переводы' и описание вида 'Имя Ф.' (одно слово, пробел, заглавная буква и точка).
    """
    logger.info("Старт transfer_search")
    transfer_pattern = re.compile(r"^\w+\s[А-ЯЁ]\b\.?$", re.IGNORECASE)

    def is_individual_transfer(transaction: Dict) -> bool:
        cat = str(transaction.get("Категория", ""))
        desc = str(transaction.get("Описание", ""))
        return cat == "Переводы" and bool(transfer_pattern.match(desc.strip()))

    result = list(filter(is_individual_transfer, data))
    logger.info(f"Найдено переводов физлицам: {len(result)}")
    return json.dumps(result, ensure_ascii=False, default=str)
