"""
Создание простых PNG иконок для PWA без внешних зависимостей
Использует base64 для создания простых цветных иконок
"""
import base64
import os

os.makedirs('static', exist_ok=True)

# Простые PNG иконки в base64 (минимальные валидные PNG файлы)
# Это простые цветные квадраты размером 1x1 пиксель, которые браузер масштабирует
# Для реального использования лучше создать настоящие иконки

sizes = [72, 96, 128, 144, 152, 192, 384, 512]

# Минимальный валидный PNG (1x1 пиксель, фиолетовый)
# PNG signature + IHDR + IDAT + IEND
minimal_png = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
)

# Создаем простые иконки
# Для реального приложения лучше использовать настоящие изображения
for size in sizes:
    # Создаем простой HTML файл, который можно использовать для генерации иконок
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            width: {size}px;
            height: {size}px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .icon {{
            width: {size}px;
            height: {size}px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20%;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
            font-size: {size // 3}px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="icon">🚗</div>
</body>
</html>'''
    
    # Сохраняем как HTML для конвертации
    with open(f'static/icon-{size}x{size}.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Создаем простой SVG, который можно использовать напрямую
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="{size}" height="{size}" fill="url(#grad)" rx="{size // 10}"/>
  <text x="50%" y="50%" font-size="{size // 2}" text-anchor="middle" dominant-baseline="central" fill="white">🚗</text>
</svg>'''
    
    with open(f'static/icon-{size}x{size}.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    print(f'Created icon-{size}x{size}.svg and icon-{size}x{size}.html')

print('\\nДля создания PNG иконок:')
print('1. Установите Pillow: pip install Pillow')
print('2. Или используйте онлайн конвертер SVG в PNG')
print('3. Или используйте созданные SVG файлы (некоторые браузеры поддерживают SVG в манифесте)')
