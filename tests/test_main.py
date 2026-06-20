from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from src.main import generate_all_reports


@pytest.fixture
def sample_df():
    dates = [datetime(2026, 6, 1), datetime(2026, 6, 5)]
    categories = ["Еда", "Транспорт"]
    amounts = [-500, -300]
    descriptions = ["Пятёрочка", "Автобус"]
    return pd.DataFrame(
        {
            "Дата операции": dates,
            "Категория": categories,
            "Сумма платежа": amounts,
            "Описание": descriptions,
            "Номер карты": ["1234", "5678"],
            "Статус": ["OK", "OK"],
        }
    )


@pytest.fixture
def sample_settings():
    return {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}


def test_generate_all_reports_structure(sample_df, sample_settings):
    # Мокаем все внешние вызовы, чтобы изолироваться от API и файловой системы
    with patch("src.main.generate_main_page", return_value={"mock_main": True}) as mock_main, patch(
        "src.main.cashback_categories", return_value='{"Супермаркеты": 10}'
    ) as mock_cashback, patch("src.main.simple_search", return_value="[]") as mock_simple, patch(
        "src.main.phone_search", return_value="[]"
    ) as mock_phone, patch(
        "src.main.transfer_search", return_value="[]"
    ) as mock_transfer, patch(
        "src.main.spending_by_category", return_value=pd.DataFrame({"sum": [100]})
    ) as mock_report, patch(
        "src.main.get_greeting", return_value="Добрый день"
    ):
        result = generate_all_reports(sample_df, sample_settings)

    # Проверяем наличие ключей
    expected_keys = {
        "greeting",
        "main_page",
        "cashback_categories",
        "simple_search",
        "phone_search",
        "transfer_search",
        "category_report",
    }
    assert expected_keys.issubset(result.keys())

    # Проверяем, что функции были вызваны с правильными аргументами
    mock_main.assert_called_once_with(sample_df, sample_settings)
    mock_cashback.assert_called_once()
    # проверяем, что cashback_categories вызван с текущим годом и месяцем
    args, kwargs = mock_cashback.call_args
    now = datetime.now()
    assert args[1] == now.year
    assert args[2] == now.month
    # simple_search ищет "супермаркет"
    mock_simple.assert_called_once()
    assert mock_simple.call_args[0][1] == "супермаркет"
    mock_phone.assert_called_once()
    mock_transfer.assert_called_once()
    mock_report.assert_called_once_with(sample_df, "Еда")

    # Проверяем приветствие
    assert result["greeting"] == "Добрый день"
    # Проверяем, что cashback_categories распарсился
    assert result["cashback_categories"] == {"Супермаркеты": 10}
    # Проверяем, что category_report – список
    assert isinstance(result["category_report"], list)


def test_generate_all_reports_with_error_in_report(sample_df, sample_settings):
    # Проверка обработки исключения в отчёте
    with patch("src.main.generate_main_page", return_value={}), patch(
        "src.main.cashback_categories", return_value="{}"
    ), patch("src.main.simple_search", return_value="[]"), patch("src.main.phone_search", return_value="[]"), patch(
        "src.main.transfer_search", return_value="[]"
    ), patch(
        "src.main.spending_by_category", side_effect=Exception("DB error")
    ), patch(
        "src.main.get_greeting", return_value=""
    ):
        result = generate_all_reports(sample_df, sample_settings)
    assert result["category_report"] == []  # пустой список при ошибке
