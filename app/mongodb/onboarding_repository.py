"""
Репозиторий для управления процессом онбординга и калибровки параметров пользователя.
Обеспечивает сохранение и отслеживание результатов первичной и повторной калибровки,
а также управление персонализированными настройками пользователя.
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import logging
from bson import ObjectId
from pymongo import ReturnDocument

from app.core.database.mongodb import get_mongodb

logger = logging.getLogger(__name__)


class OnboardingStage(str, Enum):
    """Этапы процесса онбординга."""
    WELCOME = "welcome"                      # Приветствие и введение
    PROFILE_SETUP = "profile_setup"          # Настройка профиля (имя, аватар)
    NEEDS_ASSESSMENT = "needs_assessment"    # Оценка потребностей
    CHRONOTYPE_TEST = "chronotype_test"      # Определение хронотипа
    GOALS_SETTING = "goals_setting"          # Установка личных целей
    LIFESTYLE_SURVEY = "lifestyle_survey"    # Анкета образа жизни
    CALIBRATION = "calibration"              # Калибровка параметров
    PROBLEM_AREAS = "problem_areas"          # Выявление проблемных областей
    INITIAL_RECOMMENDATIONS = "initial_recommendations"  # Начальные рекомендации
    COMPLETED = "completed"                  # Завершение онбординга


class ChronotypeCategory(str, Enum):
    """Категории хронотипов."""
    DOLPHIN = "dolphin"       # Дельфин (проблемы с засыпанием, чуткий сон)
    LION = "lion"             # Лев (раннее пробуждение, высокая продуктивность утром)
    BEAR = "bear"             # Медведь (цикл сна-бодрствования соответствует солнечному циклу)
    WOLF = "wolf"             # Волк (позднее засыпание, высокая продуктивность вечером)


class OnboardingRepository:
    """
    Репозиторий для управления процессом онбординга и калибровки параметров пользователя.
    Обеспечивает сохранение результатов и отслеживание прогресса.
    """
    
    # Имя коллекции в MongoDB
    COLLECTION_NAME = "user_onboarding"
    
    def __init__(self, db=None):
        """
        Инициализация репозитория с опциональным соединением к БД.
        
        Args:
            db: Объект соединения с MongoDB или None для отложенного подключения
        """
        self.db = db
    
    async def get_db(self):
        """
        Получение подключения к базе данных MongoDB.
        
        Returns:
            Соединение с MongoDB
        """
        if self.db is None:
            self.db = await get_mongodb()
        return self.db
    
    async def init_collection(self):
        """
        Инициализирует коллекцию в MongoDB, создавая необходимые индексы.
        """
        db = await self.get_db()
        
        # Создаем индексы для быстрого поиска
        await db[self.COLLECTION_NAME].create_index("user_id")
        await db[self.COLLECTION_NAME].create_index([("user_id", 1), ("version", -1)])
        await db[self.COLLECTION_NAME].create_index([("user_id", 1), ("created_at", -1)])
        
        # Индекс для поиска пользователей на определенном этапе онбординга
        await db[self.COLLECTION_NAME].create_index([("current_stage", 1), ("is_completed", 1)])
        
        logger.info(f"Initialized collection {self.COLLECTION_NAME} with indexes")
    
    async def create_onboarding_profile(self, user_id: str) -> str:
        """
        Создает новый профиль онбординга для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            ID созданного профиля
        """
        db = await self.get_db()
        
        # Проверяем, существует ли уже профиль
        existing = await db[self.COLLECTION_NAME].find_one({
            "user_id": user_id,
            "is_completed": False
        })
        
        if existing:
            return str(existing["_id"])
        
        # Создаем новый профиль
        now = datetime.utcnow()
        profile = {
            "user_id": user_id,
            "version": 1,  # Версия профиля (для отслеживания перекалибровок)
            "created_at": now,
            "updated_at": now,
            "current_stage": OnboardingStage.WELCOME,
            "completed_stages": [],
            "is_completed": False,
            "completion_date": None,
            
            # Прогресс по каждому этапу (в процентах)
            "stage_progress": {
                stage.value: 0 for stage in OnboardingStage
            },
            
            # Данные, собранные во время онбординга
            "profile_data": {},
            "needs_data": {},
            "chronotype_data": {},
            "goals_data": {},
            "lifestyle_data": {},
            "calibration_data": {},
            "problem_areas_data": {},
            
            # Результаты калибровки
            "personal_settings": {
                "chronotype": None,
                "energy_peak_hours": [],
                "focus_peak_hours": [],
                "sleep_preferences": {},
                "activity_preferences": {},
                "learning_style": None,
                "stress_triggers": [],
                "coping_strategies": []
            }
        }
        
        result = await db[self.COLLECTION_NAME].insert_one(profile)
        return str(result.inserted_id)
    
    async def get_onboarding_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает текущий профиль онбординга пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Профиль онбординга или None, если не найден
        """
        db = await self.get_db()
        
        # Находим последний (активный или завершенный) профиль
        profile = await db[self.COLLECTION_NAME].find_one(
            {"user_id": user_id},
            sort=[("version", -1)]
        )
        
        if profile:
            profile["_id"] = str(profile["_id"])
        
        return profile
    
    async def get_onboarding_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Получает информацию о прогрессе онбординга пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с информацией о прогрессе
        """
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return {
                "is_started": False,
                "is_completed": False,
                "current_stage": None,
                "progress_percent": 0,
                "completed_stages": []
            }
        
        # Рассчитываем общий прогресс
        total_stages = len(OnboardingStage)
        completed_stages = len(profile["completed_stages"])
        current_stage_progress = profile["stage_progress"].get(profile["current_stage"], 0)
        
        # Общий прогресс (завершенные этапы + процент текущего)
        if total_stages > 0:
            # Каждый этап имеет равный вес
            stage_weight = 1.0 / total_stages
            progress_percent = (completed_stages * stage_weight + (current_stage_progress / 100) * stage_weight) * 100
        else:
            progress_percent = 0
        
        return {
            "is_started": True,
            "is_completed": profile["is_completed"],
            "current_stage": profile["current_stage"],
            "progress_percent": round(progress_percent, 2),
            "completed_stages": profile["completed_stages"],
            "stage_progress": profile["stage_progress"]
        }
    
    async def update_onboarding_stage(
        self,
        user_id: str,
        stage: OnboardingStage,
        progress: int = 0,
        stage_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обновляет текущий этап онбординга пользователя.
        
        Args:
            user_id: ID пользователя
            stage: Новый этап
            progress: Прогресс по этапу (0-100)
            stage_data: Данные, собранные на этапе
            
        Returns:
            Обновленный профиль
        """
        db = await self.get_db()
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            profile_id = await self.create_onboarding_profile(user_id)
            profile = await db[self.COLLECTION_NAME].find_one({"_id": ObjectId(profile_id)})
        
        # Определяем, завершен ли предыдущий этап
        current_stage = profile["current_stage"]
        current_progress = profile["stage_progress"].get(current_stage, 0)
        
        updates = {
            "updated_at": datetime.utcnow(),
        }
        
        # Если текущий этап был завершен (100%), добавляем его в список завершенных
        if current_progress == 100 and current_stage != stage and current_stage not in profile["completed_stages"]:
            updates["completed_stages"] = profile["completed_stages"] + [current_stage]
        
        # Обновляем текущий этап и его прогресс
        updates["current_stage"] = stage
        updates["stage_progress." + stage] = progress
        
        # Если предоставлены данные этапа, сохраняем их в соответствующем поле
        if stage_data:
            if stage == OnboardingStage.PROFILE_SETUP:
                updates["profile_data"] = stage_data
            elif stage == OnboardingStage.NEEDS_ASSESSMENT:
                updates["needs_data"] = stage_data
            elif stage == OnboardingStage.CHRONOTYPE_TEST:
                updates["chronotype_data"] = stage_data
            elif stage == OnboardingStage.GOALS_SETTING:
                updates["goals_data"] = stage_data
            elif stage == OnboardingStage.LIFESTYLE_SURVEY:
                updates["lifestyle_data"] = stage_data
            elif stage == OnboardingStage.CALIBRATION:
                updates["calibration_data"] = stage_data
            elif stage == OnboardingStage.PROBLEM_AREAS:
                updates["problem_areas_data"] = stage_data
        
        # Проверяем, не является ли этот этап завершающим
        if stage == OnboardingStage.COMPLETED and progress == 100:
            updates["is_completed"] = True
            updates["completion_date"] = datetime.utcnow()
        
        # Обновляем профиль
        updated_profile = await db[self.COLLECTION_NAME].find_one_and_update(
            {"_id": ObjectId(profile["_id"])},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_profile:
            updated_profile["_id"] = str(updated_profile["_id"])
        
        return updated_profile
    
    async def save_chronotype_results(
        self,
        user_id: str,
        chronotype: ChronotypeCategory,
        test_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Сохраняет результаты теста хронотипа и обновляет персональные настройки.
        
        Args:
            user_id: ID пользователя
            chronotype: Определенный хронотип
            test_results: Результаты теста
            
        Returns:
            Обновленный профиль
        """
        db = await self.get_db()
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return None
        
        # Определяем пиковые часы на основе хронотипа
        energy_peak_hours = []
        focus_peak_hours = []
        sleep_preferences = {}
        
        if chronotype == ChronotypeCategory.DOLPHIN:
            energy_peak_hours = [10, 11, 12, 13, 14]
            focus_peak_hours = [15, 16, 17, 18]
            sleep_preferences = {
                "ideal_bedtime": "23:30-00:30",
                "ideal_waketime": "06:30-07:30",
                "sleep_duration": "6-7"
            }
        elif chronotype == ChronotypeCategory.LION:
            energy_peak_hours = [6, 7, 8, 9, 10]
            focus_peak_hours = [8, 9, 10, 11]
            sleep_preferences = {
                "ideal_bedtime": "22:00-23:00",
                "ideal_waketime": "05:00-06:00",
                "sleep_duration": "7-8"
            }
        elif chronotype == ChronotypeCategory.BEAR:
            energy_peak_hours = [8, 9, 10, 11, 12, 13]
            focus_peak_hours = [10, 11, 12, 13, 14]
            sleep_preferences = {
                "ideal_bedtime": "23:00-00:00",
                "ideal_waketime": "07:00-08:00",
                "sleep_duration": "8"
            }
        elif chronotype == ChronotypeCategory.WOLF:
            energy_peak_hours = [12, 13, 14, 15, 16, 17, 18]
            focus_peak_hours = [17, 18, 19, 20, 21]
            sleep_preferences = {
                "ideal_bedtime": "00:00-01:00",
                "ideal_waketime": "08:00-09:00",
                "sleep_duration": "7-8"
            }
        
        # Обновляем персональные настройки
        updates = {
            "updated_at": datetime.utcnow(),
            "personal_settings.chronotype": chronotype,
            "personal_settings.energy_peak_hours": energy_peak_hours,
            "personal_settings.focus_peak_hours": focus_peak_hours,
            "personal_settings.sleep_preferences": sleep_preferences,
            "chronotype_data": test_results
        }
        
        # Обновляем прогресс этапа
        updates["stage_progress." + OnboardingStage.CHRONOTYPE_TEST] = 100
        
        # Обновляем профиль
        updated_profile = await db[self.COLLECTION_NAME].find_one_and_update(
            {"_id": ObjectId(profile["_id"])},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_profile:
            updated_profile["_id"] = str(updated_profile["_id"])
        
        return updated_profile
    
    async def save_needs_priorities(
        self,
        user_id: str,
        needs_priorities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Сохраняет приоритеты потребностей пользователя.
        
        Args:
            user_id: ID пользователя
            needs_priorities: Список приоритетов потребностей
                [{"need_id": "...", "importance": 0.8, "target_satisfaction": 4.0}, ...]
            
        Returns:
            Обновленный профиль
        """
        db = await self.get_db()
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return None
        
        updates = {
            "updated_at": datetime.utcnow(),
            "needs_data.priorities": needs_priorities,
            "stage_progress." + OnboardingStage.NEEDS_ASSESSMENT: 100
        }
        
        # Обновляем профиль
        updated_profile = await db[self.COLLECTION_NAME].find_one_and_update(
            {"_id": ObjectId(profile["_id"])},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_profile:
            updated_profile["_id"] = str(updated_profile["_id"])
        
        return updated_profile
    
    async def save_personal_goals(
        self,
        user_id: str,
        personal_goals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Сохраняет личные цели пользователя.
        
        Args:
            user_id: ID пользователя
            personal_goals: Список личных целей
                [{"title": "...", "category": "...", "target_date": "...", "priority": 5}, ...]
            
        Returns:
            Обновленный профиль
        """
        db = await self.get_db()
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return None
        
        updates = {
            "updated_at": datetime.utcnow(),
            "goals_data.personal_goals": personal_goals,
            "stage_progress." + OnboardingStage.GOALS_SETTING: 100
        }
        
        # Обновляем профиль
        updated_profile = await db[self.COLLECTION_NAME].find_one_and_update(
            {"_id": ObjectId(profile["_id"])},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_profile:
            updated_profile["_id"] = str(updated_profile["_id"])
        
        return updated_profile
    
    async def save_problem_areas(
        self,
        user_id: str,
        problem_areas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Сохраняет проблемные области пользователя.
        
        Args:
            user_id: ID пользователя
            problem_areas: Список проблемных областей
                [{"area": "sleep", "severity": 3, "details": "..."}, ...]
            
        Returns:
            Обновленный профиль
        """
        db = await self.get_db()
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return None
        
        updates = {
            "updated_at": datetime.utcnow(),
            "problem_areas_data.areas": problem_areas,
            "stage_progress." + OnboardingStage.PROBLEM_AREAS: 100
        }
        
        # Обновляем профиль
        updated_profile = await db[self.COLLECTION_NAME].find_one_and_update(
            {"_id": ObjectId(profile["_id"])},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_profile:
            updated_profile["_id"] = str(updated_profile["_id"])
        
        return updated_profile
    
    async def save_lifestyle_survey(
        self,
        user_id: str,
        lifestyle_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Сохраняет данные опроса об образе жизни.
        
        Args:
            user_id: ID пользователя
            lifestyle_data: Данные опроса об образе жизни
            
        Returns:
            Обновленный профиль
        """
        db = await self.get_db()
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return None
        
        updates = {
            "updated_at": datetime.utcnow(),
            "lifestyle_data": lifestyle_data,
            "stage_progress." + OnboardingStage.LIFESTYLE_SURVEY: 100
        }
        
        # Обновляем персональные настройки на основе данных об образе жизни
        activity_preferences = {}
        learning_style = None
        stress_triggers = []
        coping_strategies = []
        
        # Определяем предпочтения активности
        if "exercise_preference" in lifestyle_data:
            activity_preferences["exercise_type"] = lifestyle_data["exercise_preference"]
        
        if "exercise_duration" in lifestyle_data:
            activity_preferences["duration"] = lifestyle_data["exercise_duration"]
        
        if "exercise_frequency" in lifestyle_data:
            activity_preferences["frequency"] = lifestyle_data["exercise_frequency"]
        
        # Определяем стиль обучения
        if "learning_preference" in lifestyle_data:
            learning_style = lifestyle_data["learning_preference"]
        
        # Определяем триггеры стресса
        if "stress_triggers" in lifestyle_data:
            stress_triggers = lifestyle_data["stress_triggers"]
        
        # Определяем стратегии совладания
        if "coping_strategies" in lifestyle_data:
            coping_strategies = lifestyle_data["coping_strategies"]
        
        # Дополняем обновления
        updates["personal_settings.activity_preferences"] = activity_preferences
        updates["personal_settings.learning_style"] = learning_style
        updates["personal_settings.stress_triggers"] = stress_triggers
        updates["personal_settings.coping_strategies"] = coping_strategies
        
        # Обновляем профиль
        updated_profile = await db[self.COLLECTION_NAME].find_one_and_update(
            {"_id": ObjectId(profile["_id"])},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_profile:
            updated_profile["_id"] = str(updated_profile["_id"])
        
        return updated_profile
    
    async def complete_calibration(
        self,
        user_id: str,
        calibration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Завершает калибровку и сохраняет окончательные параметры.
        
        Args:
            user_id: ID пользователя
            calibration_data: Данные калибровки
            
        Returns:
            Обновленный профиль
        """
        db = await self.get_db()
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return None
        
        # Получаем персональные настройки
        personal_settings = profile.get("personal_settings", {})
        
        # Обновляем их данными калибровки
        for key, value in calibration_data.items():
            personal_settings[key] = value
        
        updates = {
            "updated_at": datetime.utcnow(),
            "calibration_data": calibration_data,
            "personal_settings": personal_settings,
            "stage_progress." + OnboardingStage.CALIBRATION: 100
        }
        
        # Обновляем профиль
        updated_profile = await db[self.COLLECTION_NAME].find_one_and_update(
            {"_id": ObjectId(profile["_id"])},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if updated_profile:
            updated_profile["_id"] = str(updated_profile["_id"])
        
        return updated_profile
    
    async def start_recalibration(self, user_id: str) -> Dict[str, Any]:
        """
        Начинает процесс перекалибровки параметров пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Новый профиль перекалибровки
        """
        db = await self.get_db()
        
        # Получаем текущий профиль
        current_profile = await self.get_onboarding_profile(user_id)
        
        if not current_profile:
            # Если профиля нет, создаем новый
            profile_id = await self.create_onboarding_profile(user_id)
            return await db[self.COLLECTION_NAME].find_one({"_id": ObjectId(profile_id)})
        
        # Формируем базовые данные для нового профиля
        now = datetime.utcnow()
        new_version = current_profile.get("version", 0) + 1
        
        # Копируем базовые данные из текущего профиля
        new_profile = {
            "user_id": user_id,
            "version": new_version,
            "created_at": now,
            "updated_at": now,
            "current_stage": OnboardingStage.CHRONOTYPE_TEST,  # Начинаем с теста хронотипа
            "completed_stages": [],
            "is_completed": False,
            "completion_date": None,
            
            # Прогресс по каждому этапу (в процентах)
            "stage_progress": {
                stage.value: 0 for stage in OnboardingStage
            },
            
            # Копируем профиль и другие данные из предыдущей версии
            "profile_data": current_profile.get("profile_data", {}),
            "needs_data": {},
            "chronotype_data": {},
            "goals_data": current_profile.get("goals_data", {}),
            "lifestyle_data": {},
            "calibration_data": {},
            "problem_areas_data": {},
            
            # Копируем текущие настройки как базовые
            "personal_settings": current_profile.get("personal_settings", {})
        }
        
        # Сохраняем новый профиль
        result = await db[self.COLLECTION_NAME].insert_one(new_profile)
        new_profile_id = str(result.inserted_id)
        
        # Получаем и возвращаем полный новый профиль
        created_profile = await db[self.COLLECTION_NAME].find_one({"_id": ObjectId(new_profile_id)})
        if created_profile:
            created_profile["_id"] = str(created_profile["_id"])
        
        return created_profile
    
    async def get_personal_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Получает персональные настройки пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с персональными настройками
        """
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile or not profile.get("is_completed"):
            return {}
        
        return profile.get("personal_settings", {})
    
    async def export_onboarding_data(self, user_id: str) -> Dict[str, Any]:
        """
        Экспортирует все данные онбординга пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Полный набор данных онбординга
        """
        profile = await self.get_onboarding_profile(user_id)
        
        if not profile:
            return {}
        
        # Формируем структурированный экспорт данных
        export_data = {
            "user_id": user_id,
            "onboarding_version": profile.get("version", 1),
            "completion_status": {
                "is_completed": profile.get("is_completed", False),
                "completion_date": profile.get("completion_date"),
                "current_stage": profile.get("current_stage"),
                "progress": {stage: progress for stage, progress in profile.get("stage_progress", {}).items()}
            },
            "personal_profile": profile.get("profile_data", {}),
            "chronotype": {
                "type": profile.get("personal_settings", {}).get("chronotype"),
                "test_results": profile.get("chronotype_data", {})
            },
            "needs": profile.get("needs_data", {}),
            "goals": profile.get("goals_data", {}),
            "lifestyle": profile.get("lifestyle_data", {}),
            "problem_areas": profile.get("problem_areas_data", {}),
            "calibration": profile.get("calibration_data", {}),
            "personal_settings": profile.get("personal_settings", {})
        }
        
        return export_data