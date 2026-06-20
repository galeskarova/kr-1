from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.reports import report_decorator, spending_by_category


@pytest.fixture
def sample_df():
    """DataFrame с разными категориями и датами."""
    dates = [
        datetime(2026, 6, 1),
        datetime(2026, 5, 15),
        datetime(2026, 4, 10),
        datetime(2026, 3, 5),
        datetime(2026, 2, 1),
        datetime(2026, 5, 20),
        datetime(2026, 6, 10),
    ]
    categories = ["Еда", "Еда", "Еда", "Транспорт", "Еда", "Еда", "Транспорт"]
    amounts = [-500, -300, -200, -100, -50, -150, -75]
    descriptions = [f"Описание {i}" for i in range(len(dates))]
    statuses = ["OK"] * len(dates)

    return pd.DataFrame(
        {
            "Дата операции": dates,
            "Категория": categories,
            "Сумма платежа": amounts,
            "Описание": descriptions,
            "Статус": statuses,
        }
    )


def test_spending_by_category_basic(sample_df):
    # Тест за последние 3 месяца от 2026-06-15
    result = spending_by_category(sample_df, "Еда", "2026-06-15")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 4  # за период с ~15.03.2026 по 15.06.2026: 1 апр, 15 мая, 20 мая, 1 июня? проверим
    # даты: 2026-03-05 раньше чем start_date (15 марта) не попадает
    # 2026-02-01 - нет, 2026-04-10 - попадает, 2026-05-15 и 05-20, 06-01 - попадают. Итого 4.
    assert all(result["Категория"] == "Еда")
    assert all(result["Сумма платежа"] < 0)


def test_spending_by_category_no_date(sample_df):
    with patch("src.reports.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 6, 15, 12, 0, 0)
        result = spending_by_category(sample_df, "Еда")
    # Должно работать как с датой 2026-06-15
    assert len(result) == 4


def test_spending_by_category_empty(sample_df):
    result = spending_by_category(sample_df, "Несуществующая", "2026-06-15")
    assert result.empty


def test_spending_by_category_other_date(sample_df):
    # Для даты 2026-03-01 и категории "Транспорт" нет подходящих транзакций
    # (все транзакции "Транспорт" позже этой даты)
    result = spending_by_category(sample_df, "Транспорт", "2026-03-01")
    assert len(result) == 0


def test_spending_by_category_not_expense(sample_df):
    # Добавим положительную сумму, она не должна войти
    df = sample_df.copy()
    df.loc[len(df)] = [datetime(2026, 5, 1), "Еда", 100, "Возврат", "OK"]
    result = spending_by_category(df, "Еда", "2026-06-15")
    # Положительная сумма не входит
    assert all(result["Сумма платежа"] < 0)


def test_spending_by_category_sort_order(sample_df):
    result = spending_by_category(sample_df, "Еда", "2026-06-15")
    dates = result["Дата операции"].tolist()
    assert dates == sorted(dates, reverse=True)


# Тесты декоратора
def test_report_decorator_no_arg(tmp_path):
    @report_decorator
    def dummy_report():
        return pd.DataFrame({"a": [1, 2]})

    result = dummy_report()
    # Проверим, что файл создан
    report_file = Path("dummy_report_report.json")
    assert report_file.exists()
    saved = pd.read_json(report_file)
    pd.testing.assert_frame_equal(saved, result)
    # Удалим, чтобы не мусорить
    report_file.unlink()


def test_report_decorator_with_filename(tmp_path, monkeypatch):
    filename = tmp_path / "my_report.json"
    monkeypatch.chdir(tmp_path)  # чтобы относительный путь работал внутри tmp_path

    @report_decorator(filename=str(filename))
    def another_report():
        return pd.DataFrame({"b": [3, 4]})

    result = another_report()
    assert filename.exists()
    saved = pd.read_json(filename)
    pd.testing.assert_frame_equal(saved, result)


def test_report_decorator_with_str(tmp_path, monkeypatch):
    # Использование декоратора с параметром без имени
    @report_decorator("custom_name.json")
    def str_report():
        return pd.DataFrame({"c": [5]})

    monkeypatch.chdir(tmp_path)
    result = str_report()
    assert Path("custom_name.json").exists()
    saved = pd.read_json("custom_name.json")
    pd.testing.assert_frame_equal(saved, result)


def test_report_decorator_preserves_return(tmp_path):
    @report_decorator
    def report():
        return pd.DataFrame({"d": [6]})

    result = report()
    assert isinstance(result, pd.DataFrame)
    assert result.iloc[0, 0] == 6
