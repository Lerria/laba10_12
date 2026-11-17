class ExpenseError(Exception):
    """Базовий клас для всіх помилок програми."""


class ValidationError(ExpenseError):
    """Користувач ввів некоректне значення (дата, сума, категорія)."""


class DataFormatError(ExpenseError):
    """Файл має невірний формат або в ньому немає потрібних стовпців."""


class EmptyDataError(ExpenseError):
    """Немає даних для аналізу або побудови графіків."""
