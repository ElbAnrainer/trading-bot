from data import get_data
from strategy import check_signal

df = get_data("AAPL")

print("Columns:", df.columns)
print(df.tail())

signal = check_signal(df)
print("Signal:", signal)
