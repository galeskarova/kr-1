import pandas as pd

from src.utils import fetch_currency_rates, fetch_stock_prices, get_greeting


def generate_main_page(transactions_df: pd.DataFrame, settings: dict) -> dict:
    """
    Формирует JSON-представление главной страницы.

    :param transactions_df: DataFrame с транзакциями.
    :param settings: словарь настроек, содержащий 'user_currencies' и 'user_stocks'.
    :return: словарь с блоками greeting, cards, top_transactions, currency_rates,
             stock_prices, top_categories.
    """
    # Только успешные операции
    df = transactions_df[transactions_df.get("Статус", "") == "OK"].copy()

    # 1. Приветствие
    greeting = get_greeting()

    # 2. Информация по картам
    cards = []
    # Группируем по номеру карты (последние 4 цифры)
    for card_number, group in df.groupby("Номер карты", dropna=True):
        # Расходы (сумма < 0), поступления (сумма > 0)
        expenses = group.loc[group["Сумма платежа"] < 0, "Сумма платежа"].sum()
        income = group.loc[group["Сумма платежа"] > 0, "Сумма платежа"].sum()
        cards.append(
            {
                "last_digits": str(card_number),
                "total_expense": int(abs(expenses)),  # округляем до целых
                "total_income": int(income),
            }
        )

    # 3. Топ-5 транзакций по убыванию amount (Сумма платежа)
    top5 = df.nlargest(5, "Сумма платежа")
    top_transactions = []
    for _, row in top5.iterrows():
        top_transactions.append(
            {
                "date": pd.Timestamp(row["Дата операции"]).strftime("%d.%m.%Y"),
                "amount": row["Сумма платежа"],
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )

    # 4. Курсы валют и котировки акций с обработкой ошибок API
    user_currencies = settings.get("user_currencies", [])
    user_stocks = settings.get("user_stocks", [])

    try:
        rates = fetch_currency_rates(user_currencies)
    except Exception:
        rates = {}
    try:
        stocks = fetch_stock_prices(user_stocks)
    except Exception:
        stocks = {}

    currency_rates = [{"currency": curr, "rate": rate} for curr, rate in rates.items() if rate > 0]
    stock_prices = [{"stock": st, "price": price} for st, price in stocks.items() if price > 0]

    # 5. Топ-7 категорий расходов с выделением Переводов и Наличных
    expenses_df = df[df["Сумма платежа"] < 0].copy()
    if not expenses_df.empty:
        expenses_df["amount_abs"] = expenses_df["Сумма платежа"].abs()
        cat_sum = expenses_df.groupby("Категория")["amount_abs"].sum().reset_index()
        cat_sum = cat_sum.sort_values("amount_abs", ascending=False)
    else:
        cat_sum = pd.DataFrame(columns=["Категория", "amount_abs"])

    top_categories = []
    special_cats = {"Переводы", "Наличные"}
    other_sum = 0

    for i, (_, row) in enumerate(cat_sum.iterrows()):
        cat = row["Категория"]
        amt = int(row["amount_abs"])
        if i < 7:
            top_categories.append({"category": cat, "amount": amt})
        else:
            if cat in special_cats:
                # Если спецкатегория не попала в топ-7, добавляем её отдельно
                top_categories.append({"category": cat, "amount": amt})
            else:
                other_sum += amt

    if other_sum > 0:
        top_categories.append({"category": "Остальное", "amount": int(other_sum)})

    return {
        "greeting": greeting,
        "cards": cards,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
        "top_categories": top_categories,
    }
