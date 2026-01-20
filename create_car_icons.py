#!/usr/bin/env python3
"""
Скрипт для создания иконок автомобиля из SVG
"""

import os
import sys

def create_simple_png_icons():
    """Создает PNG иконки из SVG используя простой метод"""
    
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    print("Создание PNG иконок из SVG...")
    
    # Проверяем наличие Pillow
    try:
        from PIL import Image, ImageDraw
        from xml.etree import ElementTree as ET
        import io
        
        # Читаем SVG
        with open('static/icon-car.svg', 'r', encoding='utf-8') as f:
            svg_content = f.read()
        
        # Парсим SVG для получения размеров
        root = ET.fromstring(svg_content)
        viewbox = root.get('viewBox', '0 0 512 512')
        _, _, width, height = map(float, viewbox.split())
        
        for size in sizes:
            # Создаем изображение
            img = Image.new('RGB', (size, size), color='white')
            draw = ImageDraw.Draw(img)
            
            # Масштаб
            scale = size / width
            
            # Рисуем автомобиль (упрощенная версия)
            # Тень
            shadow_y = int(420 * scale)
            draw.line([(int(50 * scale), shadow_y), (int(462 * scale), shadow_y)], fill='black', width=max(2, int(3 * scale)))
            
            # Кузов автомобиля (обновленные координаты)
            body_points = [
                (int(80 * scale), int(350 * scale)),
                (int(95 * scale), int(285 * scale)),
                (int(140 * scale), int(255 * scale)),
                (int(190 * scale), int(245 * scale)),
                (int(290 * scale), int(245 * scale)),
                (int(340 * scale), int(255 * scale)),
                (int(385 * scale), int(285 * scale)),
                (int(400 * scale), int(350 * scale)),
                (int(400 * scale), int(385 * scale)),
                (int(385 * scale), int(395 * scale)),
                (int(125 * scale), int(395 * scale)),
                (int(100 * scale), int(385 * scale)),
                (int(80 * scale), int(385 * scale)),
            ]
            draw.polygon(body_points, fill='black')
            
            # Окна
            # Переднее окно
            front_window = [
                (int(140 * scale), int(255 * scale)),
                (int(190 * scale), int(245 * scale)),
                (int(190 * scale), int(305 * scale)),
                (int(140 * scale), int(315 * scale)),
            ]
            draw.polygon(front_window, fill='white')
            
            # Заднее окно
            back_window = [
                (int(290 * scale), int(245 * scale)),
                (int(340 * scale), int(255 * scale)),
                (int(340 * scale), int(315 * scale)),
                (int(290 * scale), int(305 * scale)),
            ]
            draw.polygon(back_window, fill='white')
            
            # Колеса
            wheel_radius = int(38 * scale)
            wheel_center_radius = int(22 * scale)
            
            # Переднее колесо
            front_wheel_x = int(180 * scale)
            front_wheel_y = int(385 * scale)
            draw.ellipse([front_wheel_x - wheel_radius, front_wheel_y - wheel_radius,
                         front_wheel_x + wheel_radius, front_wheel_y + wheel_radius], fill='black')
            draw.ellipse([front_wheel_x - wheel_center_radius, front_wheel_y - wheel_center_radius,
                         front_wheel_x + wheel_center_radius, front_wheel_y + wheel_center_radius], fill='white')
            
            # Звезда на переднем колесе
            star_points = []
            for i in range(5):
                angle = (i * 144 - 90) * 3.14159 / 180
                outer_x = front_wheel_x + int(wheel_center_radius * 0.8 * __import__('math').cos(angle))
                outer_y = front_wheel_y + int(wheel_center_radius * 0.8 * __import__('math').sin(angle))
                star_points.extend([outer_x, outer_y])
            if len(star_points) >= 6:
                draw.polygon([(star_points[i], star_points[i+1]) for i in range(0, len(star_points), 2)], fill='black')
            
            # Заднее колесо
            back_wheel_x = int(330 * scale)
            back_wheel_y = int(385 * scale)
            draw.ellipse([back_wheel_x - wheel_radius, back_wheel_y - wheel_radius,
                         back_wheel_x + wheel_radius, back_wheel_y + wheel_radius], fill='black')
            draw.ellipse([back_wheel_x - wheel_center_radius, back_wheel_y - wheel_center_radius,
                         back_wheel_x + wheel_center_radius, back_wheel_y + wheel_center_radius], fill='white')
            
            # Звезда на заднем колесе
            star_points = []
            for i in range(5):
                angle = (i * 144 - 90) * 3.14159 / 180
                outer_x = back_wheel_x + int(wheel_center_radius * 0.8 * __import__('math').cos(angle))
                outer_y = back_wheel_y + int(wheel_center_radius * 0.8 * __import__('math').sin(angle))
                star_points.extend([outer_x, outer_y])
            if len(star_points) >= 6:
                draw.polygon([(star_points[i], star_points[i+1]) for i in range(0, len(star_points), 2)], fill='black')
            
            # Сохраняем
            filename = f'static/icon-{size}x{size}.png'
            img.save(filename, 'PNG')
            print(f"Создана иконка: {filename}")
        
        # Копируем 192x192 как favicon
        favicon = Image.open('static/icon-192x192.png')
        favicon.save('static/favicon.ico', 'ICO')
        print("Создан favicon.ico")
        
        print("\nВсе иконки успешно созданы!")
        return True
        
    except ImportError:
        print("Pillow не установлен. Используем альтернативный метод...")
        return create_simple_icons_fallback(sizes)
    except Exception as e:
        print(f"Ошибка при создании иконок: {e}")
        return create_simple_icons_fallback(sizes)

def create_simple_icons_fallback(sizes):
    """Простой метод создания иконок без Pillow"""
    import subprocess
    
    print("Попытка использовать другие инструменты...")
    # Если есть другие инструменты, можно использовать их
    print("Пожалуйста, установите Pillow: pip install Pillow")
    return False

if __name__ == '__main__':
    create_simple_png_icons()
