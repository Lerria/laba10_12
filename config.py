"""Модуль налаштувань програми.

Налаштування зберігаються у файлі config.json, тому їх можна змінювати
без зміни програмного коду (через меню "Налаштування" або вручну).
"""
import json
import os

# Значення за замовчуванням: використовуються, якщо файлу ще немає
DEFAULTS = {
    "currency": "грн",
    "monthly_limit": 20000.0,       # місячний ліміт витрат
    "output_dir": "output",         # папка для графіків і звітів
    "chart_dpi": 120,               # якість збережених графіків
    "date_format": "%Y-%m-%d",      # формат дати для введення
    "categories": ["Їжа", "Транспорт", "Житло", "Розваги",
                   "Здоров'я", "Одяг", "Навчання", "Інше"],
}


class Config:
    """Клас для читання, зміни та збереження налаштувань."""

    def __init__(self, path="config.json"):
        self._path = path
        self._values = dict(DEFAULTS)   # приватний словник (інкапсуляція)
        self.warning = ""               # повідомлення, якщо файл пошкоджений
        self.load()

    def load(self):
        """Завантажує налаштування з файлу. Якщо файлу немає — створює його."""
        if not os.path.exists(self._path):
            self.save()
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("очікувався JSON-об'єкт")
            self._values.update(data)
        except (OSError, ValueError) as err:   # JSONDecodeError є ValueError
            self.warning = (f"Файл налаштувань пошкоджено ({err}). "
                            "Використано значення за замовчуванням.")

    def save(self):
        """Записує поточні налаштування у файл."""
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._values, f, ensure_ascii=False, indent=2)

    def get(self, key):
        return self._values.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self._values[key] = value

    @property
    def output_dir(self):
        """Повертає папку результатів і створює її, якщо її немає."""
        folder = self.get("output_dir")
        os.makedirs(folder, exist_ok=True)
        return folder
