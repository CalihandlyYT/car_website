# Конфигурация Gunicorn для продакшена
import multiprocessing

# Количество воркеров (обычно 2-4 * количество CPU)
workers = multiprocessing.cpu_count() * 2 + 1

# Адрес и порт для прослушивания
bind = "0.0.0.0:8000"

# Имя приложения
wsgi_app = "main:app"

# Таймауты
timeout = 120
keepalive = 5

# Логирование
accesslog = "-"  # stdout
errorlog = "-"  # stderr
loglevel = "info"

# Перезагрузка при изменении кода (только для разработки)
reload = False

# Имя процесса
proc_name = "car_website"
