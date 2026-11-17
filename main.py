"""Точка входу програми «Облік особистих витрат».

Додаткові параметри командного рядка:
  --config  шлях до файлу налаштувань (за замовчуванням config.json)
  --data    файл з даними, який потрібно відкрити під час запуску
"""
import argparse

from config import Config
from data_manager import ExpenseData
from errors import ExpenseError
from gui import ExpenseApp


def main():
    parser = argparse.ArgumentParser(description="Облік особистих витрат")
    parser.add_argument("--config", default="config.json", help="файл налаштувань")
    parser.add_argument("--data", default=None, help="файл даних (CSV/JSON/XLSX)")
    args = parser.parse_args()

    config = Config(args.config)
    data = ExpenseData(config.get("date_format"))
    startup_error = None
    if args.data:
        try:
            data.load(args.data)
        except (FileNotFoundError, ExpenseError) as err:
            startup_error = str(err)

    app = ExpenseApp(config, data)
    if startup_error:
        app.after(300, lambda: app._error(startup_error))
    app.mainloop()


if __name__ == "__main__":
    main()
