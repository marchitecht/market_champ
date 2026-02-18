from pytrends.request import TrendReq

keyword = "робот пылесос"
pytrends = TrendReq(hl="ru-RU", tz=180)
pytrends.build_payload([keyword], timeframe="today 3-m", geo="RU")
data = pytrends.interest_over_time()

print(data)
