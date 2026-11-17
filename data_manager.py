"""Модуль роботи з даними: введення, очищення, фільтрація, імпорт/експорт.

Використовується бібліотека pandas. Дані зберігаються у таблиці DataFrame
зі стовпцями: date, category, description, amount.
"""
import json
import os
from datetime import datetime

import pandas as pd

from errors import DataFormatError, ValidationError

COLUMNS = ["date", "category", "description", "amount"]


class ExpenseData:
    """Клас-сховище витрат. Сама таблиця прихована (приватний атрибут)."""

    def __init__(self, date_format="%Y-%m-%d"):
        self._df = pd.DataFrame(columns=COLUMNS)
        self._date_format = date_format

    #  доступ до даних
    @property
    def dataframe(self):
        """Повертає копію таблиці, щоб її не змінили ззовні."""
        return self._df.copy()

    def __len__(self):
        return len(self._df)

    def categories(self):
        """Список категорій, які є в даних."""
        return sorted(self._df["category"].dropna().unique().tolist())

    #  додавання / видалення
    def parse_date(self, text):
        """Перетворює рядок на дату або кидає ValidationError."""
        try:
            return datetime.strptime(text.strip(), self._date_format)
        except (ValueError, AttributeError):
            example = datetime.now().strftime(self._date_format)
            raise ValidationError(f"Некоректна дата «{text}». Приклад: {example}")

    def add_record(self, date_text, category, description, amount_text):
        """Перевіряє введені значення та додає новий запис."""
        date = self.parse_date(date_text)
        category = (category or "").strip()
        if not category:
            raise ValidationError("Оберіть або введіть категорію.")
        try:
            amount = float(str(amount_text).replace(",", ".").replace(" ", ""))
        except ValueError:
            raise ValidationError(f"Сума «{amount_text}» не є числом.")
        if amount <= 0:
            raise ValidationError("Сума має бути більшою за нуль.")
        row = pd.DataFrame([{"date": pd.Timestamp(date), "category": category,
                             "description": (description or "").strip(),
                             "amount": round(amount, 2)}])
        self._df = pd.concat([self._df, row], ignore_index=True)
        self._df["date"] = pd.to_datetime(self._df["date"])
        self._df["amount"] = self._df["amount"].astype(float)

    def delete_records(self, indexes):
        """Видаляє записи за номерами рядків."""
        self._df = self._df.drop(index=list(indexes)).reset_index(drop=True)

    def clear(self):
        self._df = pd.DataFrame(columns=COLUMNS)

    #  фільтрація
    def filter(self, category=None, date_from="", date_to=""):
        """Повертає відфільтровану таблицю (оригінал не змінюється)."""
        df = self._df
        if category and category != "Усі":
            df = df[df["category"] == category]
        if date_from.strip():
            df = df[df["date"] >= pd.Timestamp(self.parse_date(date_from))]
        if date_to.strip():
            df = df[df["date"] <= pd.Timestamp(self.parse_date(date_to))]
        return df.copy()

    #  очищення
    @staticmethod
    def clean(df):
        """Етап підготовки даних: перевірка стовпців, типів, видалення сміття.

        Повертає (очищена таблиця, кількість видалених рядків).
        """
        df = df.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]
        missing = [c for c in ("date", "category", "amount") if c not in df.columns]
        if missing:
            raise DataFormatError("У файлі немає обов'язкових стовпців: "
                                  + ", ".join(missing))
        if "description" not in df.columns:
            df["description"] = ""
        df = df[COLUMNS]
        before = len(df)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["amount"] = pd.to_numeric(
            df["amount"].astype(str).str.replace(",", ".", regex=False)
                        .str.replace(" ", "", regex=False), errors="coerce")
        df["category"] = df["category"].astype(str).str.strip()
        df["description"] = df["description"].fillna("").astype(str).str.strip()
        df = df.dropna(subset=["date", "amount"])           # некоректні рядки
        df = df[(df["amount"] > 0) & (df["category"] != "") &
                (df["category"].str.lower() != "nan")]
        df = df.drop_duplicates()                           # дублікати
        df = df.sort_values("date").reset_index(drop=True)
        return df, before - len(df)

    #  імпорт / експорт (CSV, JSON, Excel)
    def load(self, path):
        """Завантажує файл CSV / JSON / XLSX. Повертає кількість відкинутих рядків."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Файл не знайдено: {path}")
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".csv":
                raw = pd.read_csv(path, encoding="utf-8-sig", sep=None, engine="python")
            elif ext == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                if not isinstance(content, list):
                    raise DataFormatError("JSON має містити список записів.")
                raw = pd.DataFrame(content)
            elif ext in (".xlsx", ".xlsm"):
                raw = pd.read_excel(path)
            else:
                raise DataFormatError(f"Непідтримуваний формат «{ext}». "
                                      "Використайте CSV, JSON або XLSX.")
        except (ValueError, KeyError, pd.errors.ParserError,
                pd.errors.EmptyDataError) as err:
            raise DataFormatError(f"Не вдалося прочитати файл: {err}")
        self._df, removed = self.clean(raw)
        return removed

    @staticmethod
    def save(df, path):
        """Зберігає таблицю у файл CSV / JSON / XLSX залежно від розширення."""
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            out.to_csv(path, index=False, encoding="utf-8-sig")
        elif ext == ".json":
            out.to_json(path, orient="records", force_ascii=False, indent=2)
        elif ext == ".xlsx":
            out.to_excel(path, index=False, sheet_name="Витрати")
        else:
            raise DataFormatError(f"Непідтримуваний формат «{ext}».")
