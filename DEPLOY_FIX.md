# Исправление ошибки запуска контейнера

## Проблема
Контейнер перезагружается после запуска из-за:
- Неправильного порта (был 5000, нужен 8000)
- Отсутствия обработки ошибок при инициализации
- Неполного файла requirements.txt

## Что было исправлено:

### 1. Изменен порт в main.py
```python
# Было:
app.run(debug=True, host='0.0.0.0', port=5000)

# Стало:
app.run(debug=False, host='0.0.0.0', port=8000)
```

### 2. Добавлена обработка ошибок
```python
if __name__ == '__main__':
    try:
        init_db()  # Создаём БД при старте
        app.run(debug=False, host='0.0.0.0', port=8000)
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        raise
```

### 3. Обновлен requirements.txt
Добавлены все необходимые зависимости:
```
Flask==3.0.0
gunicorn==21.2.0
Pillow>=10.0.0
```

### 4. Созданы дополнительные файлы:
- `wsgi.py` - точка входа для WSGI серверов
- `gunicorn_config.py` - конфигурация для Gunicorn

## Команды для запуска на сервере:

### Вариант 1: Прямой запуск через Python
```bash
python main.py
```

### Вариант 2: Через Gunicorn (рекомендуется для продакшена)
```bash
gunicorn -c gunicorn_config.py main:app
```

Или проще:
```bash
gunicorn --bind 0.0.0.0:8000 main:app
```

### Вариант 3: Через wsgi.py
```bash
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

## Проверка перед деплоем:

1. ✅ Файл `requirements.txt` присутствует и содержит все зависимости
2. ✅ Порт изменен на 8000
3. ✅ DEBUG режим отключен для продакшена
4. ✅ Добавлена обработка ошибок при инициализации
5. ✅ Исправлены синтаксические ошибки в коде

## Если проблема сохраняется:

1. Проверьте логи контейнера:
   ```bash
   docker logs <container_id>
   ```

2. Убедитесь, что все файлы загружены на сервер:
   - main.py
   - requirements.txt
   - wsgi.py (опционально)
   - gunicorn_config.py (опционально)

3. Проверьте, что зависимости установлены:
   ```bash
   pip install -r requirements.txt
   ```

4. Проверьте права доступа к файлу базы данных:
   ```bash
   chmod 644 users.db
   ```

5. Убедитесь, что порт 8000 открыт и доступен

## Переменные окружения (опционально):

Можно настроить через переменные окружения:
```bash
export FLASK_DEBUG=False
export SECRET_KEY=your-secret-key-here
```

Или в Docker:
```yaml
environment:
  - FLASK_DEBUG=False
  - SECRET_KEY=your-secret-key
```
