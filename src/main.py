import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from src.reports import spending_by_category
from src.services import cashback_categories, phone_search, simple_search, transfer_search
from src.utils import get_greeting, load_transactions, load_user_settings
from src.views import generate_main_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_all_reports(transactions_df: pd.DataFrame, settings: dict) -> Dict[str, Any]:
    """
    Собирает все ключевые отчёты и сервисы в один словарь.
    """
    logger.info("Старт генерации сводного отчёта")

    # 1. Главная страница
    main_page = generate_main_page(transactions_df, settings)

    # 2. Сервис кешбэка за текущий месяц
    now = datetime.now()
    # Преобразуем DataFrame в список словарей и приводим даты к строке
    transactions_list = transactions_df.copy()
    transactions_list["Дата операции"] = transactions_list["Дата операции"].dt.strftime("%Y-%m-%d")
    transactions_list = transactions_list.to_dict("records")

    cashback_json = cashback_categories(transactions_list, now.year, now.month)

    # 3. Простой поиск (пример)
    search_result = simple_search(transactions_list, "супермаркет")

    # 4. Поиск телефонов
    phone_result = phone_search(transactions_list)

    # 5. Поиск переводов физлицам
    transfer_result = transfer_search(transactions_list)

    # 6. Отчёт по категории "Еда" (пример)
    try:
        category_report = spending_by_category(transactions_df, "Еда")
        category_report_json = category_report.to_json(orient="records", force_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка при формировании отчёта по категории: {e}")
        category_report_json = "[]"

    return {
        "greeting": get_greeting(),
        "main_page": main_page,
        "cashback_categories": json.loads(cashback_json),
        "simple_search": json.loads(search_result),
        "phone_search": json.loads(phone_result),
        "transfer_search": json.loads(transfer_result),
        "category_report": json.loads(category_report_json),
    }


if __name__ == "__main__":
    logger.info("Запуск приложения")
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "operations.xlsx"
    settings_path = base_dir / "user_settings.json"

    df = load_transactions(str(data_path))
    settings = load_user_settings(str(settings_path))

    result = generate_all_reports(df, settings)
    print(json.dumps(result, ensure_ascii=False, indent=2))
