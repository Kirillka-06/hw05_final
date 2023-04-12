import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    dt = datetime.date.today()
    return {
        'year': dt.year
    }
