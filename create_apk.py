#!/usr/bin/env python3
"""
Скрипт для подготовки проекта к созданию APK файла
Создает необходимые файлы и инструкции
"""

import os
import json
import shutil

def create_apk_structure():
    """Создает структуру для APK"""
    
    print("🚀 Подготовка проекта для создания APK...")
    
    # Читаем manifest.json
    with open('static/manifest.json', 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # Создаем инструкцию
    instructions = f"""
# Инструкция по созданию APK для вашего сайта

## Информация о вашем PWA:
- Название: {manifest.get('name', 'Авто-обзор')}
- Короткое название: {manifest.get('short_name', 'Авто-обзор')}
- Описание: {manifest.get('description', '')}

## Способ 1: PWA Builder (Самый простой) ⭐

1. Откройте: https://www.pwabuilder.com/
2. Введите URL вашего сайта
3. Нажмите "Start" → "Build My PWA" → "Android" → "Download"
4. Готово! APK файл будет скачан

## Способ 2: Использование ngrok для локального сайта

Если ваш сайт работает локально:

1. Установите ngrok: https://ngrok.com/download
2. Запустите ваш Flask сервер: `python main.py`
3. В другом терминале запустите: `ngrok http 5000`
4. Скопируйте HTTPS URL (например: https://abc123.ngrok.io)
5. Используйте этот URL в PWA Builder

## Способ 3: Bubblewrap (Google)

```bash
npm install -g @bubblewrap/cli
bubblewrap init --manifest=https://ваш-сайт.com/manifest.json
bubblewrap build
```

## Способ 4: Capacitor

```bash
npm install -g @capacitor/cli
npm install @capacitor/core @capacitor/cli
npx cap init "Авто-обзор" "com.autoreview.app"
npx cap add android
npx cap sync
npx cap open android
```

Затем в Android Studio: Build → Build Bundle(s) / APK(s) → Build APK(s)

## Важные замечания:

1. **HTTPS обязателен** для PWA в продакшене
2. Для локального тестирования можно использовать ngrok
3. APK файл будет весить примерно 5-15 МБ
4. После создания APK можно установить на планшет через USB или загрузить в Google Play

## Быстрый старт с ngrok:

```bash
# Терминал 1: Запустите Flask
python main.py

# Терминал 2: Запустите ngrok
ngrok http 5000

# Скопируйте HTTPS URL и используйте в PWA Builder
```
"""
    
    with open('APK_INSTRUCTIONS.md', 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print("✅ Создан файл APK_INSTRUCTIONS.md с подробными инструкциями")
    print("\n📱 Рекомендуемый способ: Используйте PWA Builder (https://www.pwabuilder.com/)")
    print("   Это самый простой и быстрый способ создать APK из вашего PWA")

if __name__ == '__main__':
    create_apk_structure()
