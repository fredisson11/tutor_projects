from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError


def health_check(request):
    """
    Перевіряє стан підключення до бази даних за замовчуванням.
    Повертає JSON-відповідь зі статусом.
    """
    db_conn = connections["default"]
    db_status = "ok"
    http_status = 200

    try:
        db_conn.cursor()
    except OperationalError:
        db_status = "unreachable"
        http_status = 503

    return JsonResponse({"database_status": db_status}, status=http_status)
