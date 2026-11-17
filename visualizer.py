"""Модуль візуалізації (matplotlib). Побудова та збереження графіків."""
import os

from matplotlib.figure import Figure

from analyzer import ExpenseAnalyzer

PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2",
           "#B279A2", "#EECA3B", "#9D755D", "#BAB0AC"]


class ChartBuilder:
    """Створює графіки як об'єкти Figure (їх можна і показати, і зберегти)."""

    # назва для користувача, внутрішній ключ
    CHARTS = {
        "Структура витрат (кругова)": "pie",
        "Витрати по місяцях (стовпчикова)": "bar",
        "Накопичені витрати (лінійна)": "line",
        "Розподіл сум (гістограма)": "hist",
    }

    def __init__(self, config):
        self._cfg = config

    def build(self, kind, analyzer: ExpenseAnalyzer):
        methods = {"pie": self._pie, "bar": self._bar,
                   "line": self._line, "hist": self._hist}
        return methods[kind](analyzer)

    def _pie(self, an):
        fig = Figure(figsize=(7, 5))
        ax = fig.add_subplot(111)
        data = an.by_category()
        ax.pie(data["total"], autopct="%1.1f%%", startangle=90,
               colors=PALETTE[:len(data)] if len(data) <= len(PALETTE) else None)
        ax.legend(data["category"], title="Категорії", loc="center left",
                  bbox_to_anchor=(1, 0.5))
        ax.set_title("Структура витрат за категоріями")
        fig.tight_layout()
        return fig

    def _bar(self, an):
        fig = Figure(figsize=(7, 5))
        ax = fig.add_subplot(111)
        m = an.by_month()
        ax.bar(m["month"], m["total"], color=PALETTE[0], label="Витрати за місяць")
        if an.limit > 0:
            ax.axhline(an.limit, color=PALETTE[3], linestyle="--",
                       label=f"Ліміт ({an.limit:,.0f} {self._cfg.get('currency')})")
        ax.set_title("Витрати по місяцях")
        ax.set_xlabel("Місяць")
        ax.set_ylabel(f"Сума, {self._cfg.get('currency')}")
        ax.grid(axis="y", alpha=0.3)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        return fig

    def _line(self, an):
        fig = Figure(figsize=(7, 5))
        ax = fig.add_subplot(111)
        c = an.cumulative()
        ax.plot(c["date"], c["cumulative"], color=PALETTE[1], linewidth=2,
                label="Накопичена сума")
        ax.set_title("Накопичені витрати")
        ax.set_xlabel("Дата")
        ax.set_ylabel(f"Сума, {self._cfg.get('currency')}")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        return fig

    def _hist(self, an):
        fig = Figure(figsize=(7, 5))
        ax = fig.add_subplot(111)
        a = an.amounts()
        ax.hist(a, bins=min(15, max(3, len(a) // 3)), color=PALETTE[2],
                edgecolor="white", label="Кількість покупок")
        ax.axvline(a.mean(), color=PALETTE[3], linestyle="--",
                   label=f"Середнє: {a.mean():,.0f}")
        ax.set_title("Розподіл розміру витрат")
        ax.set_xlabel(f"Сума однієї витрати, {self._cfg.get('currency')}")
        ax.set_ylabel("Кількість")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        return fig

    def save_all(self, analyzer, folder):
        """Зберігає всі графіки у PNG. Повертає словник {ключ: шлях}."""
        os.makedirs(folder, exist_ok=True)
        paths = {}
        for kind in self.CHARTS.values():
            fig = self.build(kind, analyzer)
            path = os.path.join(folder, f"chart_{kind}.png")
            fig.savefig(path, dpi=int(self._cfg.get("chart_dpi")))
            paths[kind] = path
        return paths
