import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def report_decorator(filename_or_func=None, *, filename: Optional[str] = None):
    """
    Декоратор для сохранения результата функции-отчёта в файл.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Определяем имя файла
            nonlocal filename
            if filename is None:
                # Имя по умолчанию: название функции + _report.json
                filename = f"{func.__name__}_report.json"
            try:
                if isinstance(result, pd.DataFrame):
                    result.to_json(filename, orient="records", force_ascii=False, indent=2)
                else:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(str(result))
                logger.info(f"Отчёт сохранён в {filename}")
            except Exception as e:
                logger.error(f"Ошибка сохранения отчёта: {e}")
            return result

        return wrapper

    if callable(filename_or_func):
        # Декоратор использован без параметров: @report_decorator
        func = filename_or_func
        filename_or_func = None
        return decorator(func)
    else:
        # Передан параметр filename
        if filename_or_func is not None:
            filename = filename_or_func
        return decorator


def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает траты по заданной категории за последние 3 месяца от переданной даты.
    """
    logger.info(f"Запуск spending_by_category: category={category}, date={date}")

    if date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(date, "%Y-%m-%d")

    start_date = end_date - timedelta(days=90)  # приблизительно 3 месяца

    # Убедимся, что колонка с датой в datetime
    if not pd.api.types.is_datetime64_any_dtype(transactions["Дата операции"]):
        transactions = transactions.copy()
        transactions["Дата операции"] = pd.to_datetime(transactions["Дата операции"])

    mask = (
        (transactions["Дата операции"] >= start_date)
        & (transactions["Дата операции"] <= end_date)
        & (transactions["Категория"] == category)
        & (transactions["Сумма платежа"] < 0)  # только расходы
    )

    result = transactions.loc[mask].copy()
    result = result.sort_values("Дата операции", ascending=False)

    logger.info(f"Найдено {len(result)} транзакций по категории '{category}'")
    return result
