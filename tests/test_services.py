import json

import pytest

from src.services import cashback_categories, investment_bank, phone_search, simple_search, transfer_search


# Фикстура с тестовыми транзакциями
@pytest.fixture
def sample_transactions():
    return [
        {
            "Дата операции": "2026-06-01",
            "Сумма операции": 1712.0,
            "Кешбэк": 17.12,
            "Категория": "Супермаркеты",
            "Описание": "Пятёрочка",
        },
        {
            "Дата операции": "2026-06-05",
            "Сумма операции": 45.0,
            "Кешбэк": 0.0,
            "Категория": "Транспорт",
            "Описание": "Метро",
        },
        {
            "Дата операции": "2026-06-10",
            "Сумма операции": 3200.0,
            "Кешбэк": 32.0,
            "Категория": "Супермаркеты",
            "Описание": "Магнит",
        },
        {
            "Дата операции": "2026-06-12",
            "Сумма операции": 100.0,
            "Кешбэк": 1.0,
            "Категория": "Транспорт",
            "Описание": "Автобус",
        },
        {
            "Дата операции": "2026-06-18",
            "Сумма операции": 500.0,
            "Кешбэк": 5.0,
            "Категория": "Кафе и рестораны",
            "Описание": "Кофейня",
        },
        {
            "Дата операции": "2026-06-20",
            "Сумма операции": 1234.56,
            "Кешбэк": 12.35,
            "Категория": "Аптеки",
            "Описание": "Лекарства",
        },
        # Операция вне июня – для проверки фильтрации
        {
            "Дата операции": "2026-05-30",
            "Сумма операции": 999.0,
            "Кешбэк": 9.99,
            "Категория": "Развлечения",
            "Описание": "Кино",
        },
    ]


# Тесты для cashback_categories


def test_cashback_categories_top3(sample_transactions):
    result_json = cashback_categories(sample_transactions, 2026, 6)
    result = json.loads(result_json)
    # Ожидаем топ-3:
    # Супермаркеты: 17.12 + 32.0 = 49.12 → 49 (int)
    # Аптеки: 12.35 → 12
    # Кафе и рестораны: 5.0 → 5
    assert len(result) == 3
    assert result == {
        "Супермаркеты": 49,
        "Аптеки": 12,
        "Кафе и рестораны": 5,
    }


def test_cashback_categories_empty(sample_transactions):
    result_json = cashback_categories(sample_transactions, 2027, 1)
    result = json.loads(result_json)
    assert result == {}


def test_cashback_categories_missing_fields():
    data = [
        {"Дата операции": "2026-06-01", "Кешбэк": 10, "Категория": "Еда"},
        {"Дата операции": "2026-06-01", "Категория": "Еда"},  # нет кешбэка
        {"Кешбэк": 20, "Категория": "Товары"},  # нет даты
    ]
    result_json = cashback_categories(data, 2026, 6)
    result = json.loads(result_json)
    # Только первая запись должна войти, кешбэк 10 → int
    assert result == {"Еда": 10}


# Тесты для investment_bank


def test_investment_bank_limit50(sample_transactions):
    # Июнь 2026: транзакции с суммой 1712, 45, 3200, 100, 500, 1234.56
    # 1712 -> 1750 (38)
    # 45 -> 50 (5)
    # 3200 -> 3200 (0)
    # 100 -> 100 (0)
    # 500 -> 500 (0)
    # 1234.56 -> 1250 (15.44)
    # Итого 38 + 5 + 0 + 0 + 0 + 15.44 = 58.44
    assert investment_bank("2026-06", sample_transactions, 50) == 58.44


def test_investment_bank_limit10():
    transactions = [
        {"Дата операции": "2026-06-05", "Сумма операции": 12.0},
        {"Дата операции": "2026-06-06", "Сумма операции": 9.0},
    ]
    # 12 -> 20 (8), 9 -> 10 (1) = 9.0
    assert investment_bank("2026-06", transactions, 10) == 9.0


def test_investment_bank_wrong_month(sample_transactions):
    # Месяц, которого нет в данных
    assert investment_bank("2026-07", sample_transactions, 50) == 0.0


def test_investment_bank_empty():
    assert investment_bank("2026-06", [], 100) == 0.0


# Тесты для simple_search


def test_simple_search_found(sample_transactions):
    result_json = simple_search(sample_transactions, "кофе")
    result = json.loads(result_json)
    assert len(result) == 1
    assert result[0]["Описание"] == "Кофейня"


def test_simple_search_case_insensitive(sample_transactions):
    result_json = simple_search(sample_transactions, "ПЯТЁРОЧКА")
    result = json.loads(result_json)
    assert len(result) == 1
    assert result[0]["Описание"] == "Пятёрочка"


def test_simple_search_not_found(sample_transactions):
    result_json = simple_search(sample_transactions, "авиабилеты")
    result = json.loads(result_json)
    assert result == []


def test_simple_search_empty_data():
    result_json = simple_search([], "что-то")
    assert json.loads(result_json) == []


# Тесты для phone_search


def test_phone_search_detects_numbers():
    data = [
        {"Описание": "Я МТС +7 921 11-22-33"},
        {"Описание": "Тинькофф Мобайл +7 995 555-55-55"},
        {"Описание": "МТС Mobile +7 981 333-44-55"},
        {"Описание": "Без номера"},
        {"Описание": "Обычный текст 1234567890"},  # не соответствует формату
    ]
    result_json = phone_search(data)
    result = json.loads(result_json)
    assert len(result) == 3


def test_phone_search_format_8():
    data = [
        {"Описание": "Пополнение 89000000000"},
        {"Описание": "Пополнение 8-900-000-00-00"},
    ]
    result_json = phone_search(data)
    result = json.loads(result_json)
    assert len(result) == 2


def test_phone_search_no_match(sample_transactions):
    result_json = phone_search(sample_transactions)
    result = json.loads(result_json)
    assert result == []


def test_phone_search_empty():
    result_json = phone_search([])
    assert json.loads(result_json) == []


# Тесты для transfer_search


def test_transfer_search_finds_individuals():
    data = [
        {"Категория": "Переводы", "Описание": "Валерий А."},
        {"Категория": "Переводы", "Описание": "Сергей З."},
        {"Категория": "Переводы", "Описание": "Артем П."},
        {"Категория": "Переводы", "Описание": "Аренда квартиры"},  # не подходит
        {"Категория": "Рестораны", "Описание": "Алексей М."},  # не та категория
    ]
    result_json = transfer_search(data)
    result = json.loads(result_json)
    assert len(result) == 3


def test_transfer_search_no_dot_still_works():
    data = [
        {"Категория": "Переводы", "Описание": "Иван И"},  # нет точки, но шаблон допускает
    ]
    result_json = transfer_search(data)
    result = json.loads(result_json)
    assert len(result) == 1


def test_transfer_search_empty():
    result_json = transfer_search([])
    assert json.loads(result_json) == []
