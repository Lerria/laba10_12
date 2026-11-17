"""Графічний інтерфейс програми (tkinter + ttk).

Клас ExpenseApp з'єднує всі модулі: дані, аналіз, графіки, звіти.
"""
import os
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analyzer import ExpenseAnalyzer
from data_manager import ExpenseData
from errors import ExpenseError, ValidationError
from exporter import ReportBuilder
from visualizer import ChartBuilder

FILETYPES = [("CSV", "*.csv"), ("JSON", "*.json"), ("Excel", "*.xlsx")]


class ExpenseApp(tk.Tk):
    """Головне вікно застосунку «Облік особистих витрат»."""

    def __init__(self, config, data: ExpenseData):
        super().__init__()
        self._cfg = config
        self._data = data
        self._charts = ChartBuilder(config)
        self._reports = ReportBuilder(config)
        self._view = data.dataframe      # поточна (відфільтрована) таблиця
        self._analyzer = None            # результат останнього аналізу
        self._canvas = None              # полотно з графіком
        self._sort_desc = False

        self.title("Облік особистих витрат")
        self.geometry("1100x680")
        self.minsize(900, 560)

        self._build_menu()
        self._build_status_bar()
        self._build_left_panel()
        self._build_tabs()
        self._apply_filter()
        if config.warning:
            self._warn(config.warning)

    # Побудова інтерфейсу
    def _build_menu(self):
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Відкрити файл (CSV/JSON/XLSX)…", command=self.on_open)
        file_menu.add_command(label="Зберегти таблицю як…", command=self.on_save_table)
        file_menu.add_separator()
        file_menu.add_command(label="Вихід", command=self.destroy)
        menu.add_cascade(label="Файл", menu=file_menu)

        rep_menu = tk.Menu(menu, tearoff=False)
        rep_menu.add_command(label="Зберегти всі графіки (PNG)", command=self.on_save_charts)
        rep_menu.add_command(label="Excel-звіт (кілька аркушів)", command=self.on_excel_report)
        rep_menu.add_command(label="HTML-звіт", command=self.on_html_report)
        menu.add_cascade(label="Звіти", menu=rep_menu)

        menu.add_command(label="Налаштування", command=self.on_settings)
        self.config(menu=menu)

    def _build_left_panel(self):
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")

        # форма додавання запису
        form = ttk.LabelFrame(left, text="Новий запис", padding=8)
        form.pack(fill="x")
        self.v_date = tk.StringVar(value=datetime.now().strftime(self._cfg.get("date_format")))
        self.v_cat = tk.StringVar()
        self.v_desc = tk.StringVar()
        self.v_amount = tk.StringVar()
        ttk.Label(form, text="Дата:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.v_date, width=22).grid(row=0, column=1, pady=2)
        ttk.Label(form, text="Категорія:").grid(row=1, column=0, sticky="w", pady=2)
        self.cb_cat = ttk.Combobox(form, textvariable=self.v_cat, width=19,
                                   values=self._cfg.get("categories"))
        self.cb_cat.grid(row=1, column=1, pady=2)
        ttk.Label(form, text="Опис:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.v_desc, width=22).grid(row=2, column=1, pady=2)
        ttk.Label(form, text="Сума:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.v_amount, width=22).grid(row=3, column=1, pady=2)
        ttk.Button(form, text="Додати запис", command=self.on_add).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        # фільтр
        flt = ttk.LabelFrame(left, text="Фільтр", padding=8)
        flt.pack(fill="x", pady=8)
        self.v_fcat = tk.StringVar(value="Усі")
        self.v_from = tk.StringVar()
        self.v_to = tk.StringVar()
        ttk.Label(flt, text="Категорія:").grid(row=0, column=0, sticky="w", pady=2)
        self.cb_fcat = ttk.Combobox(flt, textvariable=self.v_fcat, width=19,
                                    state="readonly", values=["Усі"])
        self.cb_fcat.grid(row=0, column=1, pady=2)
        ttk.Label(flt, text="Дата від:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(flt, textvariable=self.v_from, width=22).grid(row=1, column=1, pady=2)
        ttk.Label(flt, text="Дата до:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(flt, textvariable=self.v_to, width=22).grid(row=2, column=1, pady=2)
        ttk.Button(flt, text="Застосувати", command=self._apply_filter).grid(
            row=3, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(flt, text="Скинути", command=self.on_reset_filter).grid(
            row=3, column=1, sticky="ew", pady=(6, 0))

        # дії
        act = ttk.LabelFrame(left, text="Дії", padding=8)
        act.pack(fill="x")
        ttk.Button(act, text="Видалити виділені", command=self.on_delete).pack(fill="x", pady=2)
        ttk.Button(act, text="Аналізувати", command=self.on_analyze).pack(fill="x", pady=2)
        ttk.Button(act, text="Зберегти графіки", command=self.on_save_charts).pack(fill="x", pady=2)
        ttk.Button(act, text="Створити HTML-звіт", command=self.on_html_report).pack(fill="x", pady=2)

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        # вкладка 1: таблиця
        t1 = ttk.Frame(self.tabs)
        self.tabs.add(t1, text="Таблиця")
        cols = ("date", "category", "description", "amount")
        heads = {"date": "Дата", "category": "Категорія",
                 "description": "Опис", "amount": "Сума"}
        self.tree = ttk.Treeview(t1, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            self.tree.heading(c, text=heads[c], command=lambda col=c: self._sort_by(col))
            self.tree.column(c, width=100 if c != "description" else 260,
                             anchor="e" if c == "amount" else "w")
        sb = ttk.Scrollbar(t1, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # вкладка 2: результати аналізу
        t2 = ttk.Frame(self.tabs)
        self.tabs.add(t2, text="Результати аналізу")
        self.txt = tk.Text(t2, height=14, state="disabled", wrap="word", font=("Arial", 11))
        self.txt.pack(fill="x", padx=6, pady=6)
        self.cat_tree = ttk.Treeview(t2, columns=("c", "t", "s"), show="headings", height=8)
        for c, h in (("c", "Категорія"), ("t", "Сума"), ("s", "Частка, %")):
            self.cat_tree.heading(c, text=h)
            self.cat_tree.column(c, width=150, anchor="w" if c == "c" else "e")
        self.cat_tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # вкладка 3: графіки
        t3 = ttk.Frame(self.tabs)
        self.tabs.add(t3, text="Графіки")
        top = ttk.Frame(t3)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Тип графіка:").pack(side="left")
        self.v_chart = tk.StringVar(value=list(ChartBuilder.CHARTS)[0])
        cb = ttk.Combobox(top, textvariable=self.v_chart, state="readonly", width=38,
                          values=list(ChartBuilder.CHARTS))
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._draw_chart())
        self.chart_frame = ttk.Frame(t3)
        self.chart_frame.pack(fill="both", expand=True)

    def _build_status_bar(self):
        self.v_status = tk.StringVar(value="Готово до роботи.")
        bar = ttk.Label(self, textvariable=self.v_status, relief="sunken", anchor="w")
        bar.pack(side="bottom", fill="x")

    # Допоміжні методи
    def _status(self, text):
        """Інформує користувача про хід виконання."""
        self.v_status.set(text)
        self.update_idletasks()

    def _warn(self, text):
        messagebox.showwarning("Увага", text)

    def _error(self, text):
        messagebox.showerror("Помилка", text)

    def _refresh_filter_values(self):
        self.cb_fcat["values"] = ["Усі"] + self._data.categories()

    def _apply_filter(self):
        """Застосовує фільтр і оновлює таблицю."""
        try:
            self._view = self._data.filter(self.v_fcat.get(), self.v_from.get(), self.v_to.get())
        except ValidationError as err:
            self._warn(str(err))
            return
        self._refresh_filter_values()
        self._fill_table()

    def _fill_table(self):
        self.tree.delete(*self.tree.get_children())
        for idx, row in self._view.iterrows():
            self.tree.insert("", "end", iid=str(idx), values=(
                row["date"].strftime("%Y-%m-%d"), row["category"], row["description"],
                f"{row['amount']:,.2f}".replace(",", " ")))
        total = float(self._view["amount"].sum()) if len(self._view) else 0.0
        self._status(f"Записів: {len(self._view)} з {len(self._data)}. "
                     f"Сума: {total:,.2f} {self._cfg.get('currency')}")

    def _sort_by(self, col):
        """Сортування таблиці за клацанням на заголовок стовпця."""
        if self._view.empty:
            return
        self._sort_desc = not self._sort_desc
        self._view = self._view.sort_values(col, ascending=not self._sort_desc)
        self._fill_table()

    def _make_analyzer(self):
        """Створює аналізатор для поточних даних (або показує повідомлення)."""
        try:
            self._analyzer = ExpenseAnalyzer(self._view, self._cfg.get("monthly_limit"))
            return self._analyzer
        except ExpenseError as err:
            self._warn(str(err))
            return None

    # Обробники подій
    def on_add(self):
        try:
            self._data.add_record(self.v_date.get(), self.v_cat.get(),
                                  self.v_desc.get(), self.v_amount.get())
        except ValidationError as err:
            self._warn(str(err))
            return
        self.v_desc.set("")
        self.v_amount.set("")
        self._apply_filter()
        self._status("Запис додано.")

    def on_delete(self):
        selected = self.tree.selection()
        if not selected:
            self._warn("Спочатку виділіть рядки в таблиці.")
            return
        if messagebox.askyesno("Підтвердження", f"Видалити записів: {len(selected)}?"):
            self._data.delete_records(int(i) for i in selected)
            self._apply_filter()

    def on_reset_filter(self):
        self.v_fcat.set("Усі")
        self.v_from.set("")
        self.v_to.set("")
        self._apply_filter()

    def on_open(self):
        path = filedialog.askopenfilename(title="Відкрити файл", filetypes=FILETYPES)
        if not path:
            return
        try:
            self._status("Завантаження та очищення даних…")
            removed = self._data.load(path)
        except FileNotFoundError as err:
            self._error(str(err))
            return
        except ExpenseError as err:
            self._error(str(err))
            return
        except Exception as err:   # непередбачена помилка читання
            self._error(f"Неочікувана помилка: {err}")
            return
        self._apply_filter()
        messagebox.showinfo("Дані завантажено",
                            f"Завантажено записів: {len(self._data)}.\n"
                            f"Відкинуто некоректних або повторних рядків: {removed}.")

    def on_save_table(self):
        if self._view.empty:
            self._warn("Таблиця порожня, зберігати нічого.")
            return
        path = filedialog.asksaveasfilename(title="Зберегти таблицю", defaultextension=".csv",
                                            filetypes=FILETYPES)
        if not path:
            return
        try:
            ExpenseData.save(self._view, path)
            self._status(f"Таблицю збережено: {path}")
        except (ExpenseError, OSError) as err:
            self._error(f"Не вдалося зберегти файл: {err}")

    def on_analyze(self):
        an = self._make_analyzer()
        if an is None:
            return
        self._status("Виконується аналіз…")
        s = an.summary()
        cur = self._cfg.get("currency")
        lines = [
            f"Період: {s['date_from']} – {s['date_to']}",
            f"Кількість записів: {s['records']}",
            f"Загальна сума: {s['total']:,.2f} {cur}",
            f"Середня витрата: {s['mean']:,.2f} {cur}   Медіана: {s['median']:,.2f} {cur}",
            f"Стандартне відхилення: {s['std']:,.2f}",
            f"Найменша / найбільша витрата: {s['min']:,.2f} / {s['max']:,.2f} {cur}",
            f"Найбільша категорія: {s['top_category']}",
        ]
        over = an.over_limit_months()
        lines.append("Перевищення місячного ліміту: " + (", ".join(over) if over else "немає"))
        tr = an.trend()
        if tr is not None:
            word = "зростають" if tr > 0 else "зменшуються"
            lines.append(f"Тренд: витрати {word} приблизно на {abs(tr):,.2f} {cur} за місяць")
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(lines))
        self.txt.config(state="disabled")

        self.cat_tree.delete(*self.cat_tree.get_children())
        for _, r in an.by_category().iterrows():
            self.cat_tree.insert("", "end", values=(r["category"], f"{r['total']:,.2f}",
                                                    f"{r['share']:.1f}"))
        self._draw_chart()
        self.tabs.select(1)
        self._status("Аналіз завершено.")

    def _draw_chart(self):
        """Показує обраний графік усередині вікна."""
        if self._analyzer is None:
            return
        fig = self._charts.build(ChartBuilder.CHARTS[self.v_chart.get()], self._analyzer)
        if self._canvas is not None:
            self._canvas.get_tk_widget().destroy()
        self._canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def _save_charts(self, an):
        self._status("Побудова та збереження графіків…")
        return self._charts.save_all(an, self._cfg.output_dir)

    def on_save_charts(self):
        an = self._make_analyzer()
        if an is None:
            return
        try:
            paths = self._save_charts(an)
        except OSError as err:
            self._error(f"Не вдалося зберегти графіки: {err}")
            return
        self._status("Графіки збережено.")
        messagebox.showinfo("Готово", "Збережено файлів: %d\nПапка: %s"
                            % (len(paths), os.path.abspath(self._cfg.output_dir)))

    def on_excel_report(self):
        an = self._make_analyzer()
        if an is None:
            return
        path = os.path.join(self._cfg.output_dir, "report.xlsx")
        try:
            self._status("Формування Excel-звіту…")
            self._reports.build_excel(an, path)
        except (OSError, ExpenseError) as err:
            self._error(f"Не вдалося створити Excel-звіт: {err}")
            return
        self._status(f"Excel-звіт: {path}")
        messagebox.showinfo("Готово", f"Excel-звіт збережено:\n{os.path.abspath(path)}")

    def on_html_report(self):
        an = self._make_analyzer()
        if an is None:
            return
        path = os.path.join(self._cfg.output_dir, "report.html")
        try:
            paths = self._save_charts(an)
            self._status("Формування HTML-звіту…")
            self._reports.build_html(an, paths, path)
        except (OSError, ExpenseError) as err:
            self._error(f"Не вдалося створити звіт: {err}")
            return
        self._status(f"HTML-звіт: {path}")
        if messagebox.askyesno("Готово", f"Звіт збережено:\n{os.path.abspath(path)}\n\n"
                                         "Відкрити його у браузері?"):
            webbrowser.open("file://" + os.path.abspath(path))

    # Вікно налаштувань
    def on_settings(self):
        win = tk.Toplevel(self)
        win.title("Налаштування")
        win.resizable(False, False)
        win.grab_set()
        fields = [("Валюта:", "currency"), ("Місячний ліміт:", "monthly_limit"),
                  ("Папка результатів:", "output_dir"), ("DPI графіків:", "chart_dpi")]
        vars_ = {}
        for r, (label, key) in enumerate(fields):
            ttk.Label(win, text=label).grid(row=r, column=0, sticky="w", padx=8, pady=4)
            vars_[key] = tk.StringVar(value=str(self._cfg.get(key)))
            ttk.Entry(win, textvariable=vars_[key], width=28).grid(row=r, column=1, padx=8)

        def save():
            try:
                limit = float(vars_["monthly_limit"].get().replace(",", "."))
                dpi = int(vars_["chart_dpi"].get())
                if limit < 0 or not 50 <= dpi <= 600:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Увага", "Ліміт має бути числом ≥ 0, "
                                       "а DPI — цілим числом від 50 до 600.", parent=win)
                return
            self._cfg.set("currency", vars_["currency"].get().strip() or "грн")
            self._cfg.set("monthly_limit", limit)
            self._cfg.set("output_dir", vars_["output_dir"].get().strip() or "output")
            self._cfg.set("chart_dpi", dpi)
            try:
                self._cfg.save()
            except OSError as err:
                messagebox.showerror("Помилка", f"Не вдалося зберегти: {err}", parent=win)
                return
            self._status("Налаштування збережено в config.json")
            win.destroy()

        ttk.Button(win, text="Зберегти", command=save).grid(row=4, column=0, columnspan=2, pady=8)
