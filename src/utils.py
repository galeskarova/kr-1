import json
import logging
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_greeting() -> str:
    """Возвращает приветствие в зависимости от текущего времени."""
    current_hour = datetime.now().hour
    if 6 <= current_hour < 12:
        return "Доброе утро"
    elif 12 <= current_hour < 18:
        return "Добрый день"
    elif 18 <= current_hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


# Загрузка транзакций из Excel-файла
def load_transactions(file_path: str) -> pd.DataFrame:
    """
    Читает Excel-файл с транзакциями и возвращает DataFrame.
    Поле "Дата операции" приводится к datetime.
    """
    logger.info(f"Загрузка транзакций из {file_path}")
    try:
        df = pd.read_excel(file_path)
        if "Дата операции" in df.columns:
            df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
        return df
    except Exception as e:
        logger.error(f"Ошибка при чтении Excel-файла: {e}")
        raise


# Загрузка пользовательских настроек
def load_user_settings(path: str = "user_settings.json") -> dict:
    """
    Читает JSON-файл с настройками.
    Ожидаются ключи "user_currencies" и "user_stocks".
    """
    logger.info(f"Загрузка настроек из {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings
    except FileNotFoundError:
        logger.warning(f"Файл настроек {path} не найден. Используются значения по умолчанию.")
        return {"user_currencies": [], "user_stocks": []}
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return {"user_currencies": [], "user_stocks": []}


# Получение курсов валют (ЦБ РФ / exchangerate.host)
def fetch_currency_rates(currencies: List[str]) -> Dict[str, float]:
    """
    Возвращает словарь {валюта: курс} для переданного списка валют.
    Использует exchangerate.host (бесплатный API).
    Базовая валюта - RUB.
    """
    if not currencies:
        return {}

    logger.info(f"Получение курсов валют: {currencies}")
    api_key = os.getenv("EXCHANGE_RATE_API_KEY", "")  # необязательно, если ключ не нужен
    base_url = "https://api.exchangerate.host/latest"
    params = {"base": "RUB", "symbols": ",".join(currencies)}
    if api_key:
        params["access_key"] = api_key

    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if not data.get("success", True):
            logger.error(f"API вернул ошибку: {data.get('error', 'Неизвестно')}")
            return {}
        rates = data.get("rates", {})
        # Фильтруем только запрошенные валюты и проверяем положительность
        result = {curr: float(rates[curr]) for curr in currencies if curr in rates and float(rates[curr]) > 0}
        logger.info(f"Получены курсы: {result}")
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе курсов валют: {e}")
        return {}
    except (KeyError, ValueError) as e:
        logger.error(f"Ошибка обработки данных валют: {e}")
        return {}


# Получение котировок акций (Finnhub / Alpha Vantage)
def fetch_stock_prices(stocks: List[str]) -> Dict[str, float]:
    """
    Возвращает словарь {тикер: цена} для переданного списка акций.
    Использует Finnhub (требуется бесплатный API-ключ).
    Если ключ не задан, возвращает заглушку.
    """
    if not stocks:
        return {}

    logger.info(f"Получение котировок акций: {stocks}")
    api_key = os.getenv("FINNHUB_API_KEY", "")
    if not api_key:
        logger.warning("API-ключ Finnhub не задан. Возвращаются заглушки.")
        return {stock: 0.0 for stock in stocks}

    base_url = "https://finnhub.io/api/v1/quote"
    result = {}
    for stock in stocks:
        try:
            response = requests.get(base_url, params={"symbol": stock, "token": api_key}, timeout=5)
            response.raise_for_status()
            data = response.json()
            price = data.get("c", 0)  # текущая цена закрытия
            if isinstance(price, (int, float)) and price > 0:
                result[stock] = float(price)
            else:
                logger.warning(f"Некорректная цена для {stock}: {data}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса для {stock}: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Ошибка обработки данных для {stock}: {e}")

    logger.info(f"Получены котировки: {result}")
    return result
