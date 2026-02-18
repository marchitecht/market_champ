import asyncio
import os
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError

# Вставь сюда реальный токен Telegram
TELEGRAM_TOKEN = "8596429987:AAGLocRhISafgiK1gNhj1r8ojCv7WZdvRAs"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


async def get_trend(keyword, max_retries=3, delay=5):
    safe_keyword = keyword.replace(" ", "_")

    if not os.path.exists("exports"):
        os.makedirs("exports")

    # Берём только CSV файлы
    csv_files = [f for f in os.listdir("exports")
                 if f.startswith(safe_keyword) and f.endswith(".csv")]

    if csv_files:
        latest_file = sorted(csv_files)[-1]
        df = pd.read_csv(f"exports/{latest_file}", index_col=0, encoding="utf-8-sig")
        return df

    attempt = 0
    while attempt < max_retries:
        try:
            pytrends = TrendReq(hl="ru-RU", tz=180)
            pytrends.build_payload([keyword], timeframe="today 3-m", geo="RU")
            df = pytrends.interest_over_time()
            if df.empty:
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exports/{safe_keyword}_RU_{timestamp}.csv"
            df.to_csv(filename, encoding="utf-8-sig")
            return df

        except TooManyRequestsError:
            attempt += 1
            print(f"429 Too Many Requests. Попытка {attempt}/{max_retries}, ждём {delay} сек.")
            await asyncio.sleep(delay)

    return None


def analyze_trend(df, keyword):
    series = df[keyword]
    series_nonzero = series[series > 0]

    if series_nonzero.empty:
        return 0, 0, 0, 0

    avg = int(series_nonzero.mean())
    growth = int(series_nonzero.iloc[-1] - series_nonzero.iloc[0])
    last_14 = series_nonzero[-14:] if len(series_nonzero) >= 2 else series_nonzero
    momentum = int(last_14.iloc[-1] - last_14.iloc[0])
    volatility = int(np.std(series_nonzero))

    return avg, growth, momentum, volatility


def make_recommendation(avg, growth, momentum, volatility):
    if avg >= 20 and growth > 10 and momentum > 10:
        return "BUY ✅"
    elif avg >= 5 and growth >= 0:
        return "WAIT ⏳"
    else:
        return "AVOID ❌"


def plot_trend(df, keyword):
    series_nonzero = df[keyword][df[keyword] > 0]
    if series_nonzero.empty:
        return None

    plt.figure(figsize=(10, 4))
    plt.plot(series_nonzero.index, series_nonzero.values, marker='o', linestyle='-')
    plt.title(f"Тренд: {keyword} (Россия)")
    plt.xlabel("Дата")
    plt.ylabel("Интерес Google Trends (0-100)")
    plt.grid(True)

    safe_keyword = keyword.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_path = f"exports/{safe_keyword}_RU_{timestamp}.png"
    plt.tight_layout()
    plt.savefig(img_path)
    plt.close()

    if os.path.exists(img_path):
        return os.path.abspath(img_path)
    return None


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "📊 Market Scout (Россия)\n\n"
        "Используй команду:\n"
        "/scan название_товара"
    )


@dp.message(lambda m: m.text.startswith("/scan"))
async def scan(message: types.Message):
    keyword = message.text.replace("/scan", "").strip()
    if not keyword:
        await message.answer("Напиши: /scan название товара")
        return

    df = await get_trend(keyword)
    if df is None:
        await message.answer("Нет данных или слишком много запросов. Попробуй позже.")
        return

    avg, growth, momentum, volatility = analyze_trend(df, keyword)
    recommendation = make_recommendation(avg, growth, momentum, volatility)
    img_path = plot_trend(df, keyword)

    response = (
        f"📦 Анализ: {keyword}\n\n"
        f"🌍 Россия\n"
        f"Средний интерес: {avg}\n"
        f"Рост 90 дней: {growth}\n"
        f"Импульс 14 дней: {momentum}\n"
        f"Волатильность: {volatility}\n\n"
        f"💡 Рекомендация: {recommendation}"
    )

    await message.answer(response)

    if img_path:
        await message.answer_photo(
            FSInputFile(img_path),
            caption=f"📈 График тренда для '{keyword}'"
        )

    await asyncio.sleep(5)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
