from unittest.mock import patch

import pandas as pd
import pytest

from src.views import generate_main_page


@pytest.fixture
def sample_transactions_df():
    """Возвращает DataFrame с разнообразными транзакциями для тестов."""
    data = {
        "Дата операции": pd.to_datetime(
            [
                "2026-06-01",
                "2026-06-02",
                "2026-06-03",
                "2026-06-04",
                "2026-06-05",
                "2026-06-06",
                "2026-06-07",
                "2026-06-08",
                "2026-06-09",
                "2026-06-10",
                "2026-06-11",
                "2026-06-12",
                "2026-06-13",
                "2026-06-14",
                "2026-06-15",
            ]
        ),
        "Сумма платежа": [
            1000.0,
            -500.0,
            2000.0,
            -150.0,
            -300.0,
            -1200.0,
            50.0,
            -70.0,
            -200.0,
            -100.0,
            -400.0,
            -80.0,
            -600.0,
            -30.0,
            -20.0,
        ],
        "Категория": [
            "Зарплата",
            "Супермаркеты",
            "Подарок",
            "Кафе",
            "Транспорт",
            "Супермаркеты",
            "Кешбэк",
            "Транспорт",
            "Переводы",
            "Аптеки",
            "Развлечения",
            "Связь",
            "Наличные",
            "Кафе",
            "Книги",
        ],
        "Описание": [
            "Зачисление",
            "Пятёрочка",
            "Деньги от друга",
            "Кофейня",
            "Автобус",
            "Магнит",
            "Бонус",
            "Метро",
            "Валерий А.",
            "Лекарства",
            "Кино",
            "Интернет",
            "Снятие наличных",
            "Ресторан",
            "Книжный",
        ],
        "Номер карты": [
            "1234",
            "1234",
            "5678",
            "1234",
            "5678",
            "1234",
            "5678",
            "1234",
            "5678",
            "1234",
            "1234",
            "5678",
            "1234",
            "5678",
            "1234",
        ],
        "Статус": ["OK", "OK", "OK", "FAILED", "OK", "OK", "OK", "OK", "OK", "OK", "OK", "OK", "OK", "OK", "OK"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_settings():
    return {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "GOOGL"]}


def test_generate_main_page_structure(sample_transactions_df, sample_settings):
    with patch("src.views.get_greeting", return_value="Добрый день"), patch(
        "src.views.fetch_currency_rates", return_value={"USD": 75.0, "EUR": 90.0}
    ), patch("src.views.fetch_stock_prices", return_value={"AAPL": 150.0, "GOOGL": 2800.0}):
        result = generate_main_page(sample_transactions_df, sample_settings)

    # Обязательные ключи
    required = {"greeting", "cards", "top_transactions", "currency_rates", "stock_prices", "top_categories"}
    assert required.issubset(result.keys())

    # Приветствие
    assert result["greeting"] == "Добрый день"

    # Карты
    assert len(result["cards"]) == 2  # номера 1234 и 5678
    cards = {c["last_digits"]: c for c in result["cards"]}
    # Карта 1234
    assert cards["1234"]["total_expense"] == 2890  # исправлено
    assert cards["1234"]["total_income"] == 1000
    # Карта 5678
    assert cards["5678"]["total_expense"] == 610
    assert cards["5678"]["total_income"] == 2050  # 2000 + 50

    # Топ-5 транзакций
    top5 = result["top_transactions"]
    assert len(top5) == 5
    amounts = [t["amount"] for t in top5]
    assert amounts == sorted(amounts, reverse=True)
    for t in top5:
        assert "date" in t
        assert "amount" in t
        assert "category" in t
        assert "description" in t

    # Валюты и акции
    assert result["currency_rates"] == [{"currency": "USD", "rate": 75.0}, {"currency": "EUR", "rate": 90.0}]
    assert result["stock_prices"] == [{"stock": "AAPL", "price": 150.0}, {"stock": "GOOGL", "price": 2800.0}]

    # Топ-7 категорий расходов
    top_cats = result["top_categories"]
    assert any(cat["category"] == "Остальное" for cat in top_cats)
    assert any(cat["category"] == "Переводы" for cat in top_cats)
    assert any(cat["category"] == "Наличные" for cat in top_cats)
    other = next((c for c in top_cats if c["category"] == "Остальное"), None)
    assert other is not None
    assert other["amount"] == 50  # Кафе (30) + Книги (20)
    for cat in top_cats:
        assert isinstance(cat["amount"], int)


def test_empty_currencies_stocks(sample_transactions_df):
    empty_settings = {"user_currencies": [], "user_stocks": []}
    with patch("src.views.get_greeting", return_value="Доброе утро"), patch(
        "src.views.fetch_currency_rates"
    ) as mock_curr, patch("src.views.fetch_stock_prices") as mock_stock:
        result = generate_main_page(sample_transactions_df, empty_settings)
        mock_curr.assert_called_once_with([])  # вызывается с пустым списком
        mock_stock.assert_called_once_with([])
    assert result["currency_rates"] == []
    assert result["stock_prices"] == []


def test_api_errors_handled(sample_transactions_df, sample_settings):
    # fetch_currency_rates кидает исключение
    with patch("src.views.get_greeting", return_value="Добрый вечер"), patch(
        "src.views.fetch_currency_rates", side_effect=Exception("Network error")
    ), patch("src.views.fetch_stock_prices", return_value={}):
        result = generate_main_page(sample_transactions_df, sample_settings)
    assert result["currency_rates"] == []
    # fetch_stock_prices вернул пустой словарь – блок stock_prices будет пустым (цены >0 нет)
    assert result["stock_prices"] == []


def test_no_expenses(sample_transactions_df):
    # Создаём датафрейм только с положительными суммами
    df_pos = sample_transactions_df[sample_transactions_df["Сумма платежа"] > 0].copy()
    with patch("src.views.get_greeting", return_value="Доброе утро"), patch(
        "src.views.fetch_currency_rates", return_value={}
    ), patch("src.views.fetch_stock_prices", return_value={}):
        result = generate_main_page(df_pos, {})
    # top_categories должен быть пустым, так как нет расходов
    assert result["top_categories"] == []


def test_date_format(sample_transactions_df, sample_settings):
    with patch("src.views.get_greeting", return_value="Добрый день"), patch(
        "src.views.fetch_currency_rates", return_value={}
    ), patch("src.views.fetch_stock_prices", return_value={}):
        result = generate_main_page(sample_transactions_df, sample_settings)
    # Проверим, что все даты в топ-транзакциях соответствуют шаблону dd.mm.yyyy
    import re

    pattern = re.compile(r"\d{2}\.\d{2}\.\d{4}")
    for t in result["top_transactions"]:
        assert pattern.fullmatch(t["date"])
