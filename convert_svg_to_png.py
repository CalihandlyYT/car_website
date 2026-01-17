"""
Конвертация SVG иконок в PNG
Требует: pip install cairosvg или pillow
"""
import os
import sys

def convert_with_pillow():
    """Конвертация используя Pillow (если установлен)"""
    try:
        from PIL import Image, ImageDraw
        import xml.etree.ElementTree as ET
        
        sizes = [72, 96, 128, 144, 152, 192, 384, 512]
        
        for size in sizes:
            # Создаем простое изображение с градиентом
            img = Image.new('RGB', (size, size), color='#667eea')
            draw = ImageDraw.Draw(img)
            
            # Рисуем градиент (простая версия)
            for i in range(size):
                ratio = i / size
                r = int(102 + (118 - 102) * ratio)  # 667eea -> 764ba2
                g = int(126 + (75 - 126) * ratio)
                b = int(234 + (162 - 234) * ratio)
                draw.rectangle([(0, i), (size, i+1)], fill=(r, g, b))
            
            # Рисуем простую иконку автомобиля
            # Кузов
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
            img.save(f'static/icon-{size}x{size}.png', 'PNG')
            print(f'✓ Created icon-{size}x{size}.png')
        
        print('\n✅ Все PNG иконки созданы успешно!')
        return True
        
    except ImportError:
        print("Pillow не установлен. Установите: pip install Pillow")
        return False

def convert_with_cairosvg():
    """Конвертация используя CairoSVG (если установлен)"""
    try:
        import cairosvg
        
        sizes = [72, 96, 128, 144, 152, 192, 384, 512]
        
        for size in sizes:
            svg_file = f'static/icon-{size}x{size}.svg'
            png_file = f'static/icon-{size}x{size}.png'
            
            if os.path.exists(svg_file):
                cairosvg.svg2png(url=svg_file, write_to=png_file, output_width=size, output_height=size)
                print(f'✓ Converted {svg_file} -> {png_file}')
        
        print('\n✅ Все PNG иконки созданы успешно!')
        return True
        
    except ImportError:
        print("CairoSVG не установлен. Установите: pip install cairosvg")
        return False

if __name__ == '__main__':
    print("Конвертация SVG иконок в PNG...\n")
    
    # Пробуем сначала Pillow (проще)
    if convert_with_pillow():
        sys.exit(0)
    
    # Если не получилось, пробуем CairoSVG
    if convert_with_cairosvg():
        sys.exit(0)
    
    print("\nНе удалось создать PNG иконки.")
    print("Установите одну из библиотек:")
    print("  pip install Pillow")
    print("  или")
    print("  pip install cairosvg")
    print("\nИли используйте онлайн конвертер для конвертации SVG в PNG.")
