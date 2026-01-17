"""
Простой скрипт для генерации иконок PWA
Требует установки Pillow: pip install Pillow
"""
try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # Создаем папку static если её нет
    os.makedirs('static', exist_ok=True)
    
    # Размеры иконок
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    for size in sizes:
        # Создаем изображение
        img = Image.new('RGB', (size, size), color='#667eea')
        draw = ImageDraw.Draw(img)
        
        # Рисуем простую иконку автомобиля
        # Простой прямоугольник для кузова
        body_margin = size // 6
        draw.rectangle(
            [body_margin, size // 3, size - body_margin, size - body_margin],
            fill='#1e3c72',
            outline='white',
            width=max(2, size // 64)
        )
        
        # Колеса
        wheel_size = size // 8
        draw.ellipse(
            [size // 4 - wheel_size // 2, size - body_margin - wheel_size // 2,
             size // 4 + wheel_size // 2, size - body_margin + wheel_size // 2],
            fill='#2c3e50',
            outline='white',
            width=max(1, size // 128)
        )
        draw.ellipse(
            [3 * size // 4 - wheel_size // 2, size - body_margin - wheel_size // 2,
             3 * size // 4 + wheel_size // 2, size - body_margin + wheel_size // 2],
            fill='#2c3e50',
            outline='white',
            width=max(1, size // 128)
        )
        
        # Сохраняем
        img.save(f'static/icon-{size}x{size}.png')
        print(f'Created icon-{size}x{size}.png')
    
    print('All icons created successfully!')
    
except ImportError:
    import os
    print("Pillow не установлен. Создаю простые SVG иконки...")
    # Создаем простые SVG иконки
    os.makedirs('static', exist_ok=True)
    
    svg_template = '''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <rect width="{size}" height="{size}" fill="#667eea"/>
  <rect x="{margin}" y="{body_y}" width="{body_w}" height="{body_h}" fill="#1e3c72" stroke="white" stroke-width="2"/>
  <circle cx="{wheel1_x}" cy="{wheel_y}" r="{wheel_r}" fill="#2c3e50" stroke="white" stroke-width="1"/>
  <circle cx="{wheel2_x}" cy="{wheel_y}" r="{wheel_r}" fill="#2c3e50" stroke="white" stroke-width="1"/>
</svg>'''
    
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    for size in sizes:
        margin = size // 6
        body_y = size // 3
        body_w = size - 2 * margin
        body_h = size - body_y - margin
        wheel1_x = size // 4
        wheel2_x = 3 * size // 4
        wheel_y = size - margin - size // 16
        wheel_r = size // 16
        
        svg_content = svg_template.format(
            size=size, margin=margin, body_y=body_y, body_w=body_w, body_h=body_h,
            wheel1_x=wheel1_x, wheel2_x=wheel2_x, wheel_y=wheel_y, wheel_r=wheel_r
        )
        
        # Сохраняем как PNG через base64 (простой способ)
        # Но для простоты создадим HTML файл для конвертации
        with open(f'static/icon-{size}x{size}.svg', 'w') as f:
            f.write(svg_content)
        print(f'Created icon-{size}x{size}.svg')
    
    print('SVG icons created. You can convert them to PNG using online tools or install Pillow.')
