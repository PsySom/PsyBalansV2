"""
Модуль для инициализации базы данных начальными значениями (сидами).
Содержит функции для заполнения таблиц базовыми данными, необходимыми для работы приложения.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ActivityType, ActivitySubtype, NeedCategory
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def seed_activity_types(db: AsyncSession) -> None:
    """
    Заполняет таблицу типов активностей базовыми значениями, если они отсутствуют.
    """
    # Проверяем, есть ли уже записи в таблице
    result = await db.execute(select(ActivityType))
    if result.first() is not None:
        logger.info("Таблица типов активностей уже содержит данные, пропускаем инициализацию")
        return
    
    # Определяем базовые типы активностей
    activity_types = [
        {
            "name": "Физические",
            "description": "Активности, связанные с физической активностью и здоровьем тела",
            "color": "#FF5733",
            "icon": "fitness_center"
        },
        {
            "name": "Социальные",
            "description": "Активности, связанные с общением и социальным взаимодействием",
            "color": "#33A8FF",
            "icon": "people"
        },
        {
            "name": "Интеллектуальные",
            "description": "Активности, направленные на развитие ума, обучение и интеллектуальный рост",
            "color": "#33FF57",
            "icon": "book"
        },
        {
            "name": "Творческие",
            "description": "Активности, связанные с творчеством и самовыражением",
            "color": "#B033FF",
            "icon": "palette"
        },
        {
            "name": "Рабочие",
            "description": "Активности, связанные с работой и профессиональной деятельностью",
            "color": "#FFDB33",
            "icon": "work"
        },
        {
            "name": "Бытовые",
            "description": "Активности, связанные с бытом и домашними делами",
            "color": "#33FFE6",
            "icon": "home"
        },
        {
            "name": "Духовные",
            "description": "Активности, связанные с духовным ростом и практиками",
            "color": "#8C33FF",
            "icon": "spa"
        },
        {
            "name": "Отдых",
            "description": "Активности, направленные на отдых и восстановление",
            "color": "#33FFB0",
            "icon": "beach_access"
        }
    ]
    
    # Добавляем типы активностей в базу данных
    for type_data in activity_types:
        activity_type = ActivityType(**type_data)
        db.add(activity_type)
    
    await db.commit()
    logger.info(f"Добавлено {len(activity_types)} типов активностей")


async def seed_activity_subtypes(db: AsyncSession) -> None:
    """
    Заполняет таблицу подтипов активностей базовыми значениями, если они отсутствуют.
    """
    # Проверяем, есть ли уже записи в таблице
    result = await db.execute(select(ActivitySubtype))
    if result.first() is not None:
        logger.info("Таблица подтипов активностей уже содержит данные, пропускаем инициализацию")
        return
    
    # Получаем все типы активностей
    result = await db.execute(select(ActivityType))
    activity_types = {type.name: type for type in result.scalars().all()}
    
    if not activity_types:
        logger.warning("Не найдены типы активностей, невозможно добавить подтипы")
        return
    
    # Определяем подтипы для каждого типа активности
    subtypes_data = {
        "Физические": [
            {"name": "Бег", "description": "Бег, пробежки, трейлраннинг", "icon": "directions_run"},
            {"name": "Йога", "description": "Различные виды йоги и практик", "icon": "self_improvement"},
            {"name": "Силовая тренировка", "description": "Тренировки с отягощениями", "icon": "fitness_center"},
            {"name": "Кардио", "description": "Кардиотренировки (велосипед, эллипс и т.д.)", "icon": "directions_bike"},
            {"name": "Плавание", "description": "Плавание и водные виды спорта", "icon": "pool"},
            {"name": "Командные виды спорта", "description": "Футбол, волейбол, баскетбол и т.д.", "icon": "sports_soccer"},
            {"name": "Прогулка", "description": "Прогулки на свежем воздухе", "icon": "directions_walk"}
        ],
        "Социальные": [
            {"name": "Встреча с друзьями", "description": "Личные встречи с друзьями", "icon": "group"},
            {"name": "Семейное время", "description": "Время, проведенное с семьей", "icon": "family_restroom"},
            {"name": "Знакомства", "description": "Знакомство с новыми людьми", "icon": "person_add"},
            {"name": "Вечеринка", "description": "Участие в вечеринках и празднованиях", "icon": "celebration"},
            {"name": "Групповые занятия", "description": "Участие в группах по интересам", "icon": "groups"},
            {"name": "Волонтерство", "description": "Добровольческая деятельность", "icon": "volunteer_activism"}
        ],
        "Интеллектуальные": [
            {"name": "Чтение", "description": "Чтение книг, статей, журналов", "icon": "menu_book"},
            {"name": "Изучение языка", "description": "Изучение иностранных языков", "icon": "translate"},
            {"name": "Курсы/обучение", "description": "Прохождение образовательных курсов", "icon": "school"},
            {"name": "Программирование", "description": "Написание кода и программное обеспечение", "icon": "code"},
            {"name": "Игры на логику", "description": "Шахматы, головоломки, логические игры", "icon": "extension"},
            {"name": "Подкасты", "description": "Прослушивание образовательных подкастов", "icon": "podcasts"}
        ],
        "Творческие": [
            {"name": "Рисование", "description": "Рисование и живопись", "icon": "brush"},
            {"name": "Музыка", "description": "Игра на инструментах, создание музыки", "icon": "music_note"},
            {"name": "Письмо", "description": "Писательская деятельность", "icon": "edit"},
            {"name": "Рукоделие", "description": "Шитье, вязание, вышивка и т.д.", "icon": "construction"},
            {"name": "Фотография", "description": "Фотографирование и обработка фото", "icon": "photo_camera"},
            {"name": "Кулинария", "description": "Готовка и кулинарные эксперименты", "icon": "restaurant"}
        ],
        "Рабочие": [
            {"name": "Работа", "description": "Рабочее время по основной работе", "icon": "work"},
            {"name": "Встречи", "description": "Рабочие встречи и совещания", "icon": "meeting_room"},
            {"name": "Фриланс", "description": "Работа на фрилансе", "icon": "laptop"},
            {"name": "Нетворкинг", "description": "Профессиональные связи и нетворкинг", "icon": "connect_without_contact"},
            {"name": "Планирование", "description": "Планирование работы и задач", "icon": "event_note"}
        ],
        "Бытовые": [
            {"name": "Уборка", "description": "Уборка дома и помещений", "icon": "cleaning_services"},
            {"name": "Готовка", "description": "Приготовление пищи", "icon": "restaurant"},
            {"name": "Покупки", "description": "Покупка продуктов и вещей", "icon": "shopping_cart"},
            {"name": "Ремонт", "description": "Ремонт и обслуживание дома/квартиры", "icon": "handyman"},
            {"name": "Садоводство", "description": "Работа в саду или с комнатными растениями", "icon": "yard"}
        ],
        "Духовные": [
            {"name": "Медитация", "description": "Медитативные практики", "icon": "self_improvement"},
            {"name": "Молитва", "description": "Религиозные практики", "icon": "church"},
            {"name": "Йога", "description": "Духовные аспекты йоги", "icon": "yoga"},
            {"name": "Духовное чтение", "description": "Чтение духовной литературы", "icon": "auto_stories"},
            {"name": "Практики осознанности", "description": "Майндфулнесс и другие практики", "icon": "psychology"}
        ],
        "Отдых": [
            {"name": "Сон", "description": "Время, потраченное на сон", "icon": "bedtime"},
            {"name": "ТВ/Фильмы", "description": "Просмотр телевизора, фильмов, сериалов", "icon": "tv"},
            {"name": "Игры", "description": "Видеоигры и развлекательные игры", "icon": "sports_esports"},
            {"name": "Чтение для удовольствия", "description": "Чтение художественной литературы", "icon": "auto_stories"},
            {"name": "Отдых на природе", "description": "Время, проведенное на природе", "icon": "nature_people"},
            {"name": "Релаксация", "description": "Техники расслабления и отдыха", "icon": "spa"}
        ]
    }
    
    # Добавляем подтипы активностей в базу данных
    subtypes_count = 0
    
    for type_name, subtypes in subtypes_data.items():
        if type_name not in activity_types:
            logger.warning(f"Тип активности '{type_name}' не найден в базе данных")
            continue
        
        for subtype_data in subtypes:
            activity_subtype = ActivitySubtype(
                **subtype_data,
                activity_type_id=activity_types[type_name].id
            )
            db.add(activity_subtype)
            subtypes_count += 1
    
    await db.commit()
    logger.info(f"Добавлено {subtypes_count} подтипов активностей")


async def seed_need_categories(db: AsyncSession) -> None:
    """
    Заполняет таблицу категорий потребностей базовыми значениями, если они отсутствуют.
    """
    # Проверяем, есть ли уже записи в таблице
    result = await db.execute(select(NeedCategory))
    if result.first() is not None:
        logger.info("Таблица категорий потребностей уже содержит данные, пропускаем инициализацию")
        return
    
    # Определяем базовые категории потребностей
    categories = [
        {
            "name": "Физические",
            "description": "Потребности, связанные с физическим благополучием организма",
            "color": "#FF5733",
            "icon": "fitness_center",
            "display_order": 1
        },
        {
            "name": "Эмоциональные",
            "description": "Потребности, связанные с эмоциональным состоянием и переживаниями",
            "color": "#FFDB33",
            "icon": "favorite",
            "display_order": 2
        },
        {
            "name": "Когнитивные",
            "description": "Потребности, связанные с умственной деятельностью и познанием",
            "color": "#33A8FF",
            "icon": "psychology",
            "display_order": 3
        },
        {
            "name": "Социальные",
            "description": "Потребности, связанные с общением и социальным взаимодействием",
            "color": "#33FF57",
            "icon": "people",
            "display_order": 4
        },
        {
            "name": "Духовные",
            "description": "Потребности, связанные с духовным развитием, смыслом и ценностями",
            "color": "#8C33FF",
            "icon": "spa",
            "display_order": 5
        }
    ]
    
    # Добавляем категории в базу данных
    for category_data in categories:
        need_category = NeedCategory(**category_data)
        db.add(need_category)
    
    await db.commit()
    logger.info(f"Добавлено {len(categories)} категорий потребностей")


async def seed_all(db: AsyncSession) -> None:
    """
    Запускает все функции сидирования базы данных.
    """
    await seed_activity_types(db)
    await seed_activity_subtypes(db)
    await seed_need_categories(db)
    logger.info("Базовые данные успешно добавлены в базу данных")