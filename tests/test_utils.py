import json
import os
from unittest.mock import mock_open, patch

import pandas as pd
import pytest
import requests

from src.utils import (
    fetch_currency_rates,
    fetch_stock_prices,
    load_transactions,
    load_user_settings,
)

# ---------- load_transactions ----------
@patch("pandas.read_excel")
def test_load_transactions_success(mock_read_excel):
    mock_df = pd.DataFrame({
        "Дата операции": ["01.01.2023", "02.01.2023"],
        "Сумма": [-1000, -500]
    })
    mock_read_excel.return_value = mock_df

    df = load_transactions("dummy.xlsx")
    assert not df.empty
    assert "Дата операции" in df.columns
    assert df["Дата операции"].dtype == "datetime64[ns]"

@patch("pandas.read_excel", side_effect=Exception("File corrupt"))
def test_load_transactions_error(mock_read_excel):
    with pytest.raises(Exception):
        load_transactions("bad.xlsx")

# ---------- load_user_settings ----------
@patch("builtins.open", new_callable=mock_open, read_data='{"user_currencies": ["USD"], "user_stocks": ["AAPL"]}')
def test_load_user_settings_success(mock_file):
    settings = load_user_settings("fake_path.json")
    assert settings["user_currencies"] == ["USD"]
    assert settings["user_stocks"] == ["AAPL"]

@patch("builtins.open", side_effect=FileNotFoundError)
def test_load_user_settings_file_not_found(mock_file):
    settings = load_user_settings("nonexistent.json")
    assert settings == {"user_currencies": [], "user_stocks": []}

@patch("builtins.open", new_callable=mock_open, read_data="not json")
def test_load_user_settings_json_error(mock_file):
    settings = load_user_settings("bad.json")
    assert settings == {"user_currencies": [], "user_stocks": []}

# ---------- fetch_currency_rates ----------
@patch("requests.get")
def test_fetch_currency_rates_success(mock_get):
    mock_resp = mock_get.return_value
    mock_resp.json.return_value = {
        "success": True,
        "rates": {"USD": 75.5, "EUR": 80.2}
    }
    mock_resp.raise_for_status.return_value = None

    rates = fetch_currency_rates(["USD", "EUR"])
    assert rates == {"USD": 75.5, "EUR": 80.2}

@patch("requests.get")
def test_fetch_currency_rates_empty_list(mock_get):
    rates = fetch_currency_rates([])
    assert rates == {}
    mock_get.assert_not_called()

@patch("requests.get")
def test_fetch_currency_rates_api_error(mock_get):
    mock_resp = mock_get.return_value
    mock_resp.json.return_value = {"success": False, "error": "Invalid key"}
    mock_resp.raise_for_status.return_value = None

    rates = fetch_currency_rates(["USD"])
    assert rates == {}

@patch("requests.get", side_effect=requests.exceptions.ConnectionError)
def test_fetch_currency_rates_network_error(mock_get):
    rates = fetch_currency_rates(["USD"])
    assert rates == {}

# ---------- fetch_stock_prices ----------
@patch("src.utils.os.getenv", return_value="fake_api_key")
@patch("requests.get")
def test_fetch_stock_prices_success(mock_get, mock_env):
    # Настраиваем ответ для первого тикера
    mock_resp = mock_get.return_value
    mock_resp.json.return_value = {"c": 150.0}
    mock_resp.raise_for_status.return_value = None

    prices = fetch_stock_prices(["AAPL"])
    assert prices == {"AAPL": 150.0}

@patch("src.utils.os.getenv", return_value="")
def test_fetch_stock_prices_no_api_key(mock_env):
    prices = fetch_stock_prices(["AAPL"])
    assert prices == {"AAPL": 0.0}  # заглушка

@patch("src.utils.os.getenv", return_value="fake_key")
@patch("requests.get", side_effect=requests.exceptions.Timeout)
def test_fetch_stock_prices_request_error(mock_get, mock_env):
    prices = fetch_stock_prices(["AAPL"])
    assert prices == {}

@patch("src.utils.os.getenv", return_value="fake_key")
@patch("requests.get")
def test_fetch_stock_prices_partial_success(mock_get, mock_env):
    # два тикера, для одного вернётся ошибка
    def side_effect(url, params, timeout):
        resp = requests.Response()
        if params["symbol"] == "AAPL":
            resp._content = json.dumps({"c": 100.0}).encode()
            resp.status_code = 200
        else:
            resp._content = json.dumps({"c": 0}).encode()  # некорректная цена
            resp.status_code = 200
        return resp
    mock_get.side_effect = side_effect

    prices = fetch_stock_prices(["AAPL", "GOOGL"])
    assert prices == {"AAPL": 100.0}