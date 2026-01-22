"""
Система переводов для сайта
"""

# Словари переводов
TRANSLATIONS = {
    'ru': {
        # Навигация
        'favorites': '⭐ Избранное',
        'subscriptions': '📬 Подписки',
        'notifications': '🔔 Уведомления',
        'compare': '🔍 Сравнить',
        'sales': '🚗 Продажа',
        'administration': '👑 Администрация',
        'profile': '👤 Профиль',
        'logout': 'Выйти',
        'install': '📱 Установить',
        
        # Заголовки
        'best_amg_m_cars': '🏎️ Лучшие AMG и M-автомобили',
        'rating_amg_m_cars': 'Рейтинг AMG и M-автомобилей',
        
        # Фильтры
        'filters': 'Фильтры:',
        'all_categories': 'Все категории',
        'all_tags': 'Все теги',
        'reset': 'Сбросить',
        
        # Посты
        'create_post': 'Создать пост',
        'edit_post': 'Редактировать пост',
        'delete_post': 'Удалить пост',
        'read_more': 'Читать далее',
        'no_posts': 'Нет постов',
        'author': 'Автор',
        'date': 'Дата',
        'tags': 'Теги',
        'category': 'Категория',
        
        # Профиль
        'my_profile': 'Мой профиль',
        'email': 'Email',
        'rank': 'Ранг',
        'registration_date': 'Дата регистрации',
        'last_login': 'Последний вход',
        
        # Общее
        'loading': 'Загрузка...',
        'error': 'Ошибка',
        'success': 'Успешно',
        'save': 'Сохранить',
        'cancel': 'Отмена',
        'delete': 'Удалить',
        'edit': 'Редактировать',
        'search': 'Поиск',
        'back': 'Назад',
        'next': 'Далее',
        'previous': 'Назад',
        'rules': '📋 Правила',
        'rules_description': 'Пожалуйста, ознакомьтесь с правилами использования нашего сайта',
        'general_rules': 'Общие правила',
        'content_rules': 'Правила публикации контента',
        'communication_rules': 'Правила общения',
        'sales_rules': 'Правила размещения объявлений',
        'violations_rules': 'Нарушения и санкции',
        'rule_respect': 'Уважайте других пользователей и их мнение',
        'rule_language': 'Используйте вежливый и корректный язык общения',
        'rule_spam': 'Запрещено размещение спама, рекламы и нежелательного контента',
        'rule_legal': 'Соблюдайте законодательство и не нарушайте права других',
        'rule_original': 'Публикуйте только оригинальный контент или контент с указанием источника',
        'rule_quality': 'Обеспечивайте качество публикуемых материалов',
        'rule_prohibited': 'Запрещено размещение материалов, нарушающих авторские права',
        'rule_images': 'Используйте только легальные изображения и медиафайлы',
        'rule_constructive': 'Ведите конструктивные дискуссии',
        'rule_insults': 'Запрещены оскорбления, угрозы и дискриминация',
        'rule_trolling': 'Не допускается троллинг и провокации',
        'rule_privacy': 'Соблюдайте конфиденциальность личных данных других пользователей',
        'rule_accurate': 'Указывайте точную информацию об автомобиле',
        'rule_photos': 'Размещайте реальные фотографии автомобиля',
        'rule_price': 'Указывайте реальную цену без скрытых платежей',
        'rule_contact': 'Предоставляйте достоверные контактные данные',
        'rule_warning': 'За первое нарушение выдается предупреждение',
        'rule_ban': 'При повторных нарушениях возможен временный или постоянный бан',
        'rule_deletion': 'Администрация оставляет за собой право удалять контент без предупреждения',
        'rule_appeal': 'Вы можете обжаловать решение администрации',
        'important': 'Важно',
        'rule_final': 'Администрация сайта оставляет за собой право изменять правила в любое время. Продолжая использовать сайт, вы соглашаетесь с этими правилами.',
        'rules_date': 'Последнее обновление правил',
        'ban_1_day': '1-й раз: предупреждение, 2-й раз: бан на 1 день, 3-й раз: бан на 7 дней',
        'ban_3_days': '1-й раз: предупреждение, 2-й раз: бан на 3 дня, 3-й раз: бан на 14 дней',
        'ban_7_days': '1-й раз: бан на 7 дней, 2-й раз: бан на 30 дней, 3-й раз: постоянный бан',
        'ban_14_days': '1-й раз: бан на 14 дней, 2-й раз: бан на 30 дней, 3-й раз: постоянный бан',
        'ban_30_days': '1-й раз: бан на 30 дней, 2-й раз: постоянный бан',
        'ban_permanent': 'Немедленный постоянный бан',
        'ban_warning': '1-й раз: предупреждение, 2-й раз: бан на 1 день',
        'ban_schedule': 'Таблица санкций',
        'violation_type': 'Тип нарушения',
        'first_time': '1-е нарушение',
        'second_time': '2-е нарушение',
        'third_time': '3-е нарушение',
        'minor_violation': 'Незначительные нарушения',
        'medium_violation': 'Средние нарушения',
        'serious_violation': 'Серьезные нарушения',
        'critical_violation': 'Критические нарушения',
        'warning': 'Предупреждение',
        'ban_1d': 'Бан на 1 день',
        'ban_3d': 'Бан на 3 дня',
        'ban_7d': 'Бан на 7 дней',
        'ban_14d': 'Бан на 14 дней',
        'ban_30d': 'Бан на 30 дней',
        'permanent_ban': 'Постоянный бан',
        
        # Автомобили
        'engine': 'Двигатель',
        'power': 'Мощность',
        'torque': 'Крутящий момент',
        'acceleration': 'Разгон',
        'top_speed': 'Максимальная скорость',
        'price': 'Цена',
        'specifications': 'Характеристики',
        'description': 'Описание',
        
        # Продажа
        'create_sale': 'Создать объявление',
        'edit_sale': 'Редактировать объявление',
        'price_from': 'Цена от',
        'contact': 'Контакт',
        
        # Комментарии
        'comments': 'Комментарии',
        'add_comment': 'Добавить комментарий',
        'no_comments': 'Нет комментариев',
        
        # Уведомления
        'no_notifications': 'Нет уведомлений',
        'mark_all_read': 'Отметить все как прочитанные',
        
        # Подписки
        'my_subscriptions': 'Мои подписки',
        'subscribe': 'Подписаться',
        'unsubscribe': 'Отписаться',
        
        # Администрация
        'admin_panel': 'Панель администратора',
        'users': 'Пользователи',
        'ban_user': 'Забанить пользователя',
        'set_rank': 'Установить ранг',
        'monthly_reports': 'Ежемесячные отчеты',
        'reports_description': 'Статистика сайта по месяцам',
        'created_at': 'Создан',
        'total_logs': 'Логов',
        'total_posts': 'Постов',
        'total_users': 'Пользователей',
        'total_comments': 'Комментариев',
        'total_likes': 'Лайков',
        'total_views': 'Просмотров',
        'total_discussions': 'Обсуждений',
        'total_messages': 'Сообщений',
        'total_favorites': 'В избранном',
        'total_subscriptions': 'Подписок',
        'no_reports': 'Отчеты пока не созданы',
        'reports_will_appear': 'Отчеты будут автоматически создаваться каждый месяц',
        
        # Футер
        'about_us': 'О нас',
        'careers': 'Карьера',
        'terms_of_service': 'Условия использования',
        'privacy_policy': 'Политика конфиденциальности',
        'cookie_policy': 'Политика использования файлов cookie',
        'help': 'Помощь',
        'legal_information': 'Правовая информация',
    },
    'en': {
        # Navigation
        'favorites': '⭐ Favorites',
        'subscriptions': '📬 Subscriptions',
        'notifications': '🔔 Notifications',
        'compare': '🔍 Compare',
        'sales': '🚗 Sales',
        'administration': '👑 Administration',
        'profile': '👤 Profile',
        'logout': 'Logout',
        'install': '📱 Install',
        
        # Headers
        'best_amg_m_cars': '🏎️ Best AMG and M-Cars',
        'rating_amg_m_cars': 'Rating of AMG and M-Cars',
        
        # Filters
        'filters': 'Filters:',
        'all_categories': 'All Categories',
        'all_tags': 'All Tags',
        'reset': 'Reset',
        
        # Posts
        'create_post': 'Create Post',
        'edit_post': 'Edit Post',
        'delete_post': 'Delete Post',
        'read_more': 'Read More',
        'no_posts': 'No Posts',
        'author': 'Author',
        'date': 'Date',
        'tags': 'Tags',
        'category': 'Category',
        
        # Profile
        'my_profile': 'My Profile',
        'email': 'Email',
        'rank': 'Rank',
        'registration_date': 'Registration Date',
        'last_login': 'Last Login',
        
        # General
        'loading': 'Loading...',
        'error': 'Error',
        'success': 'Success',
        'save': 'Save',
        'cancel': 'Cancel',
        'delete': 'Delete',
        'edit': 'Edit',
        'search': 'Search',
        'back': 'Back',
        'next': 'Next',
        'previous': 'Previous',
        'rules': '📋 Rules',
        'rules_description': 'Please read the rules for using our site',
        'general_rules': 'General Rules',
        'content_rules': 'Content Publishing Rules',
        'communication_rules': 'Communication Rules',
        'sales_rules': 'Listing Rules',
        'violations_rules': 'Violations and Sanctions',
        'rule_respect': 'Respect other users and their opinions',
        'rule_language': 'Use polite and correct language',
        'rule_spam': 'Spam, advertising and unwanted content is prohibited',
        'rule_legal': 'Comply with the law and do not violate the rights of others',
        'rule_original': 'Publish only original content or content with source attribution',
        'rule_quality': 'Ensure the quality of published materials',
        'rule_prohibited': 'Posting materials that violate copyright is prohibited',
        'rule_images': 'Use only legal images and media files',
        'rule_constructive': 'Engage in constructive discussions',
        'rule_insults': 'Insults, threats and discrimination are prohibited',
        'rule_trolling': 'Trolling and provocation are not allowed',
        'rule_privacy': 'Respect the privacy of other users\' personal data',
        'rule_accurate': 'Provide accurate information about the car',
        'rule_photos': 'Post real photos of the car',
        'rule_price': 'Indicate the real price without hidden fees',
        'rule_contact': 'Provide reliable contact information',
        'rule_warning': 'A warning is issued for the first violation',
        'rule_ban': 'Repeated violations may result in a temporary or permanent ban',
        'rule_deletion': 'Administration reserves the right to delete content without warning',
        'rule_appeal': 'You can appeal the administration\'s decision',
        'important': 'Important',
        'rule_final': 'The site administration reserves the right to change the rules at any time. By continuing to use the site, you agree to these rules.',
        'rules_date': 'Last rules update',
        'ban_1_day': '1st time: warning, 2nd time: 1 day ban, 3rd time: 7 days ban',
        'ban_3_days': '1st time: warning, 2nd time: 3 days ban, 3rd time: 14 days ban',
        'ban_7_days': '1st time: 7 days ban, 2nd time: 30 days ban, 3rd time: permanent ban',
        'ban_14_days': '1st time: 14 days ban, 2nd time: 30 days ban, 3rd time: permanent ban',
        'ban_30_days': '1st time: 30 days ban, 2nd time: permanent ban',
        'ban_permanent': 'Immediate permanent ban',
        'ban_warning': '1st time: warning, 2nd time: 1 day ban',
        'ban_schedule': 'Sanctions Table',
        'violation_type': 'Violation Type',
        'first_time': '1st Violation',
        'second_time': '2nd Violation',
        'third_time': '3rd Violation',
        'minor_violation': 'Minor Violations',
        'medium_violation': 'Medium Violations',
        'serious_violation': 'Serious Violations',
        'critical_violation': 'Critical Violations',
        'warning': 'Warning',
        'ban_1d': '1 day ban',
        'ban_3d': '3 days ban',
        'ban_7d': '7 days ban',
        'ban_14d': '14 days ban',
        'ban_30d': '30 days ban',
        'permanent_ban': 'Permanent ban',
        
        # Cars
        'engine': 'Engine',
        'power': 'Power',
        'torque': 'Torque',
        'acceleration': 'Acceleration',
        'top_speed': 'Top Speed',
        'price': 'Price',
        'specifications': 'Specifications',
        'description': 'Description',
        
        # Sales
        'create_sale': 'Create Listing',
        'edit_sale': 'Edit Listing',
        'price_from': 'Price from',
        'contact': 'Contact',
        
        # Comments
        'comments': 'Comments',
        'add_comment': 'Add Comment',
        'no_comments': 'No Comments',
        
        # Notifications
        'no_notifications': 'No Notifications',
        'mark_all_read': 'Mark All as Read',
        
        # Subscriptions
        'my_subscriptions': 'My Subscriptions',
        'subscribe': 'Subscribe',
        'unsubscribe': 'Unsubscribe',
        
        # Administration
        'admin_panel': 'Admin Panel',
        'users': 'Users',
        'ban_user': 'Ban User',
        'set_rank': 'Set Rank',
        'monthly_reports': 'Monthly Reports',
        'reports_description': 'Site statistics by month',
        'created_at': 'Created',
        'total_logs': 'Logs',
        'total_posts': 'Posts',
        'total_users': 'Users',
        'total_comments': 'Comments',
        'total_likes': 'Likes',
        'total_views': 'Views',
        'total_discussions': 'Discussions',
        'total_messages': 'Messages',
        'total_favorites': 'Favorites',
        'total_subscriptions': 'Subscriptions',
        'no_reports': 'No reports created yet',
        'reports_will_appear': 'Reports will be automatically created every month',
        
        # Footer
        'about_us': 'About Us',
        'careers': 'Careers',
        'terms_of_service': 'Terms of Service',
        'privacy_policy': 'Privacy Policy',
        'cookie_policy': 'Cookie Policy',
        'help': 'Help',
        'legal_information': 'Legal Information',
    }
}

def get_translation(key, lang='ru'):
    """Получить перевод по ключу"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['ru']).get(key, key)

def get_current_language():
    """Получить текущий язык из сессии или по умолчанию русский"""
    from flask import session
    return session.get('language', 'ru')
