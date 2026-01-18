# Инструкция по созданию APK файла из PWA

## Способ 1: Использование PWA Builder (Рекомендуется - Самый простой)

### Шаги:
1. Перейдите на сайт: https://www.pwabuilder.com/
2. Введите URL вашего сайта (например: `https://ваш-домен.com` или `http://ваш-ip:5000`)
3. Нажмите "Start"
4. После анализа нажмите "Build My PWA"
5. Выберите "Android" → "Download"
6. Скачайте APK файл

## Способ 2: Использование Bubblewrap (Google)

### Требования:
- Node.js установлен
- Java JDK установлен

### Команды:
```bash
npm install -g @bubblewrap/cli
bubblewrap init --manifest=https://ваш-сайт.com/manifest.json
bubblewrap build
```

## Способ 3: Использование Capacitor (Более продвинутый)

### Установка:
```bash
npm install -g @capacitor/cli
npm install @capacitor/core @capacitor/cli
npx cap init
npx cap add android
npx cap sync
npx cap open android
```

Затем соберите APK в Android Studio.

## Способ 4: Онлайн-сервисы

1. **PWABuilder**: https://www.pwabuilder.com/
2. **Appy Pie**: https://www.appypie.com/
3. **GoNative**: https://gonative.io/

## Важно:
- Для создания APK нужен публичный URL сайта (HTTPS)
- Если сайт локальный, используйте ngrok или подобный сервис для создания публичного URL
- APK файл будет весить примерно 5-15 МБ
