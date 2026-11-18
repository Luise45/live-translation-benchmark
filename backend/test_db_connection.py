
from app.core.database import get_db_connection

try:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

    if result == (1,):
        print("Supabase-Backend-Anbindung erfolgreich!")

except Exception as error:
    print("Verbindung fehlgeschlagen:", type(error).__name__)
    raise
