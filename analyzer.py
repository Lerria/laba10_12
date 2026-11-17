"""Модуль аналізу даних (pandas + numpy)."""
import numpy as np
import pandas as pd

from errors import EmptyDataError


class ExpenseAnalyzer:
    """Виконує розрахунки над таблицею витрат."""

    def __init__(self, df, monthly_limit=0.0):
        if df is None or df.empty:
            raise EmptyDataError("Немає даних для аналізу. "
                                 "Додайте записи або змініть фільтр.")
        self._df = df.copy()
        self._df["month"] = self._df["date"].dt.to_period("M").astype(str)
        self._limit = float(monthly_limit)

    @property
    def dataframe(self):
        return self._df.copy()

    @property
    def limit(self):
        return self._limit

    def amounts(self):
        """Суми витрат як масив numpy."""
        return self._df["amount"].to_numpy(dtype=float)

    def summary(self):
        """Основні статистичні показники."""
        a = self.amounts()
        by_cat = self.by_category()
        return {
            "records": int(a.size),
            "total": float(np.sum(a)),
            "mean": float(np.mean(a)),
            "median": float(np.median(a)),
            "std": float(np.std(a, ddof=1)) if a.size > 1 else 0.0,
            "min": float(np.min(a)),
            "max": float(np.max(a)),
            "top_category": str(by_cat.iloc[0]["category"]),
            "date_from": self._df["date"].min().strftime("%d.%m.%Y"),
            "date_to": self._df["date"].max().strftime("%d.%m.%Y"),
        }

    def by_category(self):
        """Сума та частка кожної категорії (від більшої до меншої)."""
        g = self._df.groupby("category", as_index=False)["amount"].sum()
        g = g.rename(columns={"amount": "total"}).sort_values("total", ascending=False)
        g["share"] = g["total"] / g["total"].sum() * 100
        return g.reset_index(drop=True)

    def by_month(self):
        """Сума витрат по місяцях."""
        g = self._df.groupby("month", as_index=False)["amount"].sum()
        return g.rename(columns={"amount": "total"})

    def cumulative(self):
        """Накопичена сума витрат по днях."""
        g = self._df.groupby("date", as_index=False)["amount"].sum()
        g["cumulative"] = np.cumsum(g["amount"].to_numpy())
        return g

    def over_limit_months(self):
        """Місяці, у яких витрати перевищили ліміт."""
        if self._limit <= 0:
            return []
        m = self.by_month()
        return m[m["total"] > self._limit]["month"].tolist()

    def trend(self):
        """Середня зміна місячних витрат (кутовий коефіцієнт лінійної регресії).

        Повертає None, якщо місяців менше двох.
        """
        m = self.by_month()
        if len(m) < 2:
            return None
        x = np.arange(len(m))
        slope, _ = np.polyfit(x, m["total"].to_numpy(), 1)
        return float(slope)
