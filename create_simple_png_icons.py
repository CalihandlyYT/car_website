"""
Создание простых PNG иконок без внешних зависимостей
Использует base64 для создания минимальных валидных PNG
"""
import base64
import os

# Минимальный валидный PNG 1x1 пиксель (фиолетовый #667eea)
# Это базовый PNG, который можно использовать как заглушку
minimal_png_base64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='

os.makedirs('static', exist_ok=True)

sizes = [72, 96, 128, 144, 152, 192, 384, 512]

print("Создание простых PNG иконок...")
print("Примечание: Это минимальные PNG файлы. Для продакшена рекомендуется создать настоящие иконки.")

for size in sizes:
    # Создаем простой PNG используя base64
    # Это минимальный PNG, который будет масштабироваться браузером
    png_data = base64.b64decode(minimal_png_base64)
    
    # Сохраняем как PNG (это минимальный валидный PNG)
    with open(f'static/icon-{size}x{size}.png', 'wb') as f:
        f.write(png_data)
    
    print(f'Created icon-{size}x{size}.png (minimal)')

print("\nДля создания качественных PNG иконок:")
print("1. Установите Pillow: pip install Pillow")
print("2. Запустите: python convert_svg_to_png.py")
print("3. Или используйте онлайн конвертер SVG -> PNG")
print("4. Или используйте созданные SVG файлы (некоторые браузеры поддерживают SVG)")
