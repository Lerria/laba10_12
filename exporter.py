"""Модуль формування підсумкових звітів: HTML та Excel."""
import base64
import html
from datetime import datetime

import pandas as pd

from analyzer import ExpenseAnalyzer


class ReportBuilder:
    """Створює файли звітів на основі результатів аналізу."""

    def __init__(self, config):
        self._cfg = config

    def _summary_table(self, an):
        s = an.summary()
        cur = self._cfg.get("currency")
        rows = [
            ("Період", f"{s['date_from']} – {s['date_to']}"),
            ("Кількість записів", s["records"]),
            ("Загальна сума", f"{s['total']:,.2f} {cur}"),
            ("Середня витрата", f"{s['mean']:,.2f} {cur}"),
            ("Медіана", f"{s['median']:,.2f} {cur}"),
            ("Стандартне відхилення", f"{s['std']:,.2f}"),
            ("Мінімальна витрата", f"{s['min']:,.2f} {cur}"),
            ("Максимальна витрата", f"{s['max']:,.2f} {cur}"),
            ("Найбільша категорія", s["top_category"]),
        ]
        over = an.over_limit_months()
        rows.append(("Місяці з перевищенням ліміту", ", ".join(over) if over else "немає"))
        tr = an.trend()
        if tr is not None:
            rows.append(("Тренд (зміна за місяць)", f"{tr:+,.2f} {cur}"))
        return pd.DataFrame(rows, columns=["Показник", "Значення"])

    # Excel
    def build_excel(self, an: ExpenseAnalyzer, path):
        """Записує книгу Excel з аркушами: Витрати, Категорії, Місяці, Підсумок."""
        data = an.dataframe.drop(columns=["month"])
        cats = an.by_category().rename(columns={
            "category": "Категорія", "total": "Сума", "share": "Частка, %"})
        months = an.by_month().rename(columns={"month": "Місяць", "total": "Сума"})
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            out = data.copy()
            out["date"] = out["date"].dt.strftime("%Y-%m-%d")
            out.to_excel(writer, sheet_name="Витрати", index=False)
            cats.to_excel(writer, sheet_name="Категорії", index=False)
            months.to_excel(writer, sheet_name="Місяці", index=False)
            self._summary_table(an).to_excel(writer, sheet_name="Підсумок", index=False)
            for ws in writer.book.worksheets:          # автоширина стовпців
                for col in ws.columns:
                    width = max(len(str(c.value or "")) for c in col) + 2
                    ws.column_dimensions[col[0].column_letter].width = min(width, 45)

    # HTML
    def build_html(self, an: ExpenseAnalyzer, chart_paths, path):
        """Створює HTML-звіт із таблицями та вбудованими графіками."""
        cats = an.by_category().rename(columns={
            "category": "Категорія", "total": "Сума", "share": "Частка, %"})
        months = an.by_month().rename(columns={"month": "Місяць", "total": "Сума"})
        fmt = lambda x: f"{x:,.2f}"
        parts = [
            "<!DOCTYPE html><html lang='uk'><head><meta charset='utf-8'>",
            "<title>Звіт про витрати</title><style>",
            "body{font-family:Arial,sans-serif;max-width:900px;margin:30px auto;color:#222}",
            "table{border-collapse:collapse;margin:10px 0}",
            "td,th{border:1px solid #999;padding:5px 10px;text-align:left}",
            "th{background:#e8eef6}img{max-width:100%;margin:10px 0}",
            "</style></head><body>",
            "<h1>Звіт про особисті витрати</h1>",
            f"<p>Сформовано: {datetime.now():%d.%m.%Y %H:%M}</p>",
            "<h2>Підсумкові показники</h2>",
            self._summary_table(an).to_html(index=False, border=0),
            "<h2>Витрати за категоріями</h2>",
            cats.to_html(index=False, border=0, float_format=fmt),
            "<h2>Витрати по місяцях</h2>",
            months.to_html(index=False, border=0, float_format=fmt),
            "<h2>Графіки</h2>",
        ]
        for p in chart_paths.values():
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            parts.append(f"<img src='data:image/png;base64,{b64}' alt='{html.escape(p)}'>")
        parts.append("</body></html>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))
