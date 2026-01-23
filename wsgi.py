"""
WSGI entry point для запуска приложения через Gunicorn
"""
from main import app, ensure_scheduler_started

# Убеждаемся, что планировщик отчетов запущен при импорте через WSGI
try:
    ensure_scheduler_started()
except Exception as e:
    print(f"Предупреждение: Не удалось запустить планировщик при импорте WSGI: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=False)
