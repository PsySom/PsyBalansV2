"""
Сервис для работы с состоянием пользователя.
Реализует бизнес-логику для анализа состояния пользователя,
агрегации данных и выявления трендов.
"""
from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import json
import statistics
import numpy as np
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.orm import joinedload

from app.models.user_state import UserState
from app.mongodb.repository import MongoRepository
from app.mongodb.schemas import StateSnapshot, StateSnapshotCreate
from app.core.database.redis_client import get_cache, set_cache, invalidate_cache
from app.services.need_service import NeedService


class StateService:
    """Сервис для работы с состоянием пользователя"""
    
    def __init__(
        self, 
        db: AsyncSession,
        state_snapshot_repository=None, 
        user_state_repository=None, 
        mood_entry_repository=None, 
        need_service=None
    ):
        self.db = db
        self.state_snapshot_repository = state_snapshot_repository or MongoRepository()
        self.user_state_repository = user_state_repository
        self.mood_entry_repository = mood_entry_repository
        self.need_service = need_service or NeedService(db)
        
    async def record_state_snapshot(self, user_id: UUID, snapshot_data: StateSnapshotCreate) -> StateSnapshot:
        """
        Запись снимка состояния пользователя в MongoDB.
        Снимок содержит информацию о текущем состоянии пользователя на момент записи.
        """
        # Подготовка данных для снимка состояния
        state_snapshot = StateSnapshot(
            user_id=str(user_id),
            timestamp=snapshot_data.timestamp or datetime.now(),
            snapshot_type=snapshot_data.snapshot_type,
            mood=snapshot_data.mood.dict(),
            energy=snapshot_data.energy.dict(),
            stress=snapshot_data.stress.dict(),
            needs=snapshot_data.needs,
            focus_level=snapshot_data.focus_level,
            sleep_quality=snapshot_data.sleep_quality,
            context_factors=snapshot_data.context_factors
        )
        
        # Сохраняем снимок в MongoDB
        snapshot_id = await self.state_snapshot_repository.save_state_snapshot(state_snapshot)
        
        # Создаем запись в SQL базе для долгосрочного хранения и анализа
        state_data = {
            "user_id": user_id,
            "timestamp": state_snapshot.timestamp,
            "mood_score": state_snapshot.mood["score"],
            "energy_level": state_snapshot.energy["level"],
            "stress_level": state_snapshot.stress["level"],
            "anxiety_level": snapshot_data.anxiety_level if hasattr(snapshot_data, 'anxiety_level') else None,
            "focus_level": state_snapshot.focus_level,
            "sleep_quality": state_snapshot.sleep_quality,
            "source": "manual",
            "period_type": "instant",
            "source_details": {"snapshot_id": snapshot_id}
        }
        
        # Добавляем данные о потребностях, если они есть
        if state_snapshot.needs:
            needs_by_category = {}
            for need in state_snapshot.needs:
                # Получаем категорию потребности из базы данных
                need_obj = await self.need_service.need_repository.get_by_id_with_category(UUID(need["need_id"]))
                if need_obj:
                    category_name = need_obj.category.name.lower()
                    if category_name not in needs_by_category:
                        needs_by_category[category_name] = []
                    needs_by_category[category_name].append(need["satisfaction_level"])
            
            # Рассчитываем средние значения по категориям
            if "physical" in needs_by_category:
                state_data["physical_needs_satisfaction"] = int(sum(needs_by_category["physical"]) / len(needs_by_category["physical"]) * 10 + 50)
            if "emotional" in needs_by_category:
                state_data["emotional_needs_satisfaction"] = int(sum(needs_by_category["emotional"]) / len(needs_by_category["emotional"]) * 10 + 50)
            if "cognitive" in needs_by_category:
                state_data["cognitive_needs_satisfaction"] = int(sum(needs_by_category["cognitive"]) / len(needs_by_category["cognitive"]) * 10 + 50)
            if "social" in needs_by_category:
                state_data["social_needs_satisfaction"] = int(sum(needs_by_category["social"]) / len(needs_by_category["social"]) * 10 + 50)
            if "spiritual" in needs_by_category:
                state_data["spiritual_needs_satisfaction"] = int(sum(needs_by_category["spiritual"]) / len(needs_by_category["spiritual"]) * 10 + 50)
        
        # Создаем новую запись в UserState
        user_state = UserState(**state_data)
        
        # Рассчитываем индекс благополучия
        user_state.calculate_wellbeing_index()
        
        # Сохраняем в базу данных
        self.db.add(user_state)
        await self.db.flush()
        
        # Инвалидируем кэш состояния пользователя
        await invalidate_cache(f"user_state:{user_id}")
        
        return state_snapshot
        
    async def get_current_state(self, user_id: UUID) -> UserState:
        """
        Получение текущего состояния пользователя.
        Возвращает последнюю доступную запись состояния.
        """
        # Проверяем кэш
        cached_state = await get_cache(f"user_state:{user_id}")
        if cached_state:
            return UserState(**json.loads(cached_state))
        
        # Если в кэше нет, запрашиваем из базы
        query = (
            select(UserState)
            .where(UserState.user_id == user_id)
            .order_by(UserState.timestamp.desc())
            .limit(1)
        )
        
        result = await self.db.execute(query)
        user_state = result.scalars().first()
        
        if not user_state:
            # Если состояние не найдено, создаем новое с нейтральными показателями
            user_state = UserState(
                user_id=user_id,
                timestamp=datetime.now(),
                mood_score=0.0,
                energy_level=0.0,
                stress_level=5.0,
                period_type="instant",
                source="calculated",
                wellbeing_index=50.0
            )
        
        # Кэшируем результат
        if user_state.id:  # только если состояние уже сохранено в БД
            await set_cache(
                f"user_state:{user_id}",
                json.dumps({
                    col.name: getattr(user_state, col.name)
                    for col in user_state.__table__.columns
                    if not isinstance(getattr(user_state, col.name), (datetime, UUID))
                }),
                expires=300  # кэш на 5 минут
            )
        
        return user_state
        
    async def calculate_aggregated_state(
        self, 
        user_id: UUID, 
        period_type: str, 
        from_date: datetime, 
        to_date: datetime = None
    ) -> UserState:
        """
        Расчет агрегированного состояния за период.
        Объединяет данные из разных источников для создания целостной картины состояния.
        
        Параметры:
        - period_type: тип периода (day, week, month)
        - from_date: начало периода
        - to_date: конец периода (если не указан, используется текущее время)
        """
        if to_date is None:
            to_date = datetime.now()
            
        # Формируем ключ кэша
        cache_key = f"aggregated_state:{user_id}:{period_type}:{from_date.isoformat()}:{to_date.isoformat()}"
        
        # Проверяем кэш
        cached_state = await get_cache(cache_key)
        if cached_state:
            return UserState(**json.loads(cached_state))
            
        # Запрашиваем записи состояний из SQL базы
        query = (
            select(UserState)
            .where(
                UserState.user_id == user_id,
                UserState.timestamp >= from_date,
                UserState.timestamp <= to_date
            )
            .order_by(UserState.timestamp)
        )
        
        result = await self.db.execute(query)
        user_states = result.scalars().all()
        
        # Получаем снимки состояний из MongoDB
        snapshots = await self.state_snapshot_repository.get_state_snapshots(str(user_id))
        snapshots = [s for s in snapshots if from_date <= s.timestamp <= to_date]
        
        # Получаем записи настроения из MongoDB
        mood_entries = []
        if self.mood_entry_repository:
            mood_entries = await self.mood_entry_repository.get_mood_entries(str(user_id))
            mood_entries = [m for m in mood_entries if from_date <= m.timestamp <= to_date]
        
        # Если данных нет, возвращаем текущее состояние
        if not user_states and not snapshots and not mood_entries:
            return await self.get_current_state(user_id)
        
        # Агрегируем данные
        aggregated_data = {
            "user_id": user_id,
            "timestamp": datetime.now(),
            "period_type": period_type,
            "source": "calculated",
            "source_details": {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "user_states_count": len(user_states),
                "snapshots_count": len(snapshots),
                "mood_entries_count": len(mood_entries)
            }
        }
        
        # Агрегируем метрики состояния
        state_metrics = {}
        
        # Обрабатываем user_states
        for state in user_states:
            for column in state.__table__.columns:
                if column.name in [
                    "id", "user_id", "timestamp", "period_type", 
                    "source", "source_details", "notes", "tags",
                    "weather_data", "location_data", "activity_id", 
                    "activity_schedule_id", "created_at", "updated_at"
                ]:
                    continue
                
                value = getattr(state, column.name)
                if value is not None:
                    if column.name not in state_metrics:
                        state_metrics[column.name] = []
                    state_metrics[column.name].append(value)
        
        # Обрабатываем snapshots
        for snapshot in snapshots:
            if "mood" in snapshot.dict() and "score" in snapshot.mood:
                if "mood_score" not in state_metrics:
                    state_metrics["mood_score"] = []
                state_metrics["mood_score"].append(snapshot.mood["score"])
                
            if "energy" in snapshot.dict() and "level" in snapshot.energy:
                if "energy_level" not in state_metrics:
                    state_metrics["energy_level"] = []
                state_metrics["energy_level"].append(snapshot.energy["level"])
                
            if "stress" in snapshot.dict() and "level" in snapshot.stress:
                if "stress_level" not in state_metrics:
                    state_metrics["stress_level"] = []
                state_metrics["stress_level"].append(snapshot.stress["level"])
                
            if snapshot.focus_level:
                if "focus_level" not in state_metrics:
                    state_metrics["focus_level"] = []
                state_metrics["focus_level"].append(snapshot.focus_level)
                
            if snapshot.sleep_quality:
                if "sleep_quality" not in state_metrics:
                    state_metrics["sleep_quality"] = []
                state_metrics["sleep_quality"].append(snapshot.sleep_quality)
                
            # Обрабатываем потребности
            if snapshot.needs:
                needs_by_category = {}
                for need in snapshot.needs:
                    try:
                        # Получаем категорию потребности
                        need_obj = await self.need_service.need_repository.get_by_id_with_category(UUID(need["need_id"]))
                        if need_obj:
                            category_name = need_obj.category.name.lower()
                            if f"{category_name}_needs_satisfaction" not in state_metrics:
                                state_metrics[f"{category_name}_needs_satisfaction"] = []
                            # Преобразуем из шкалы -5..5 в 0..100
                            satisfaction_pct = int((need["satisfaction_level"] + 5) / 10 * 100)
                            state_metrics[f"{category_name}_needs_satisfaction"].append(satisfaction_pct)
                    except Exception:
                        # Пропускаем неправильные потребности
                        continue
        
        # Обрабатываем mood_entries (если они есть)
        for entry in mood_entries:
            if hasattr(entry, 'mood_score'):
                if "mood_score" not in state_metrics:
                    state_metrics["mood_score"] = []
                state_metrics["mood_score"].append(entry.mood_score)
        
        # Рассчитываем средние значения для каждой метрики
        for metric, values in state_metrics.items():
            if values:
                aggregated_data[metric] = sum(values) / len(values)
        
        # Создаем агрегированный UserState
        aggregated_state = UserState(**aggregated_data)
        
        # Рассчитываем индекс благополучия
        aggregated_state.calculate_wellbeing_index()
        
        # Кэшируем результат
        await set_cache(
            cache_key,
            json.dumps({
                col.name: getattr(aggregated_state, col.name)
                for col in aggregated_state.__table__.columns
                if not isinstance(getattr(aggregated_state, col.name), (datetime, UUID))
            }),
            expires=3600  # кэш на 1 час
        )
        
        return aggregated_state
        
    async def analyze_state_trend(
        self, 
        user_id: UUID, 
        aspect: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Анализ тренда аспекта состояния (настроение, энергия, стресс) за указанный период.
        Выявляет паттерны и тенденции.
        
        Параметры:
        - aspect: аспект состояния (mood_score, energy_level, stress_level и т.д.)
        - days: количество дней для анализа
        """
        # Проверка корректности аспекта
        valid_aspects = [
            "mood_score", "energy_level", "stress_level", "anxiety_level", 
            "focus_level", "motivation_level", "sleep_quality", "wellbeing_index"
        ]
        
        if aspect not in valid_aspects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid aspect. Valid aspects are: {', '.join(valid_aspects)}"
            )
            
        # Формируем даты для анализа
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        # Формируем ключ кэша
        cache_key = f"state_trend:{user_id}:{aspect}:{days}"
        
        # Проверяем кэш
        cached_trend = await get_cache(cache_key)
        if cached_trend:
            return json.loads(cached_trend)
        
        # Получаем данные из базы данных
        query = (
            select(UserState)
            .where(
                UserState.user_id == user_id,
                UserState.timestamp >= from_date,
                UserState.timestamp <= to_date,
                getattr(UserState, aspect) != None
            )
            .order_by(UserState.timestamp)
        )
        
        result = await self.db.execute(query)
        states = result.scalars().all()
        
        # Если данных недостаточно, пробуем получить данные из MongoDB
        if len(states) < 5 and aspect in ["mood_score", "energy_level", "stress_level"]:
            # Маппинг аспектов UserState на поля в MongoDB
            aspect_mapping = {
                "mood_score": "mood.score",
                "energy_level": "energy.level",
                "stress_level": "stress.level"
            }
            
            # Получаем снимки состояний из MongoDB
            snapshots = await self.state_snapshot_repository.get_state_snapshots(str(user_id))
            
            # Фильтруем по датам
            snapshots = [s for s in snapshots if from_date <= s.timestamp <= to_date]
            
            # Для каждого снимка добавляем соответствующие данные
            for snapshot in snapshots:
                # Проверяем, есть ли уже запись с такой датой
                timestamp = snapshot.timestamp
                exists = False
                for state in states:
                    if abs((state.timestamp - timestamp).total_seconds()) < 300:  # 5 минут
                        exists = True
                        break
                
                # Если записи нет, создаем новую
                if not exists:
                    # Получаем значение из снимка
                    if aspect == "mood_score" and "mood" in snapshot.dict() and "score" in snapshot.mood:
                        value = snapshot.mood["score"]
                    elif aspect == "energy_level" and "energy" in snapshot.dict() and "level" in snapshot.energy:
                        value = snapshot.energy["level"]
                    elif aspect == "stress_level" and "stress" in snapshot.dict() and "level" in snapshot.stress:
                        value = snapshot.stress["level"]
                    else:
                        continue
                    
                    # Создаем временную запись для анализа
                    temp_state = UserState(
                        user_id=user_id,
                        timestamp=timestamp,
                        **{aspect: value}
                    )
                    states.append(temp_state)
            
            # Сортируем по времени
            states.sort(key=lambda x: x.timestamp)
        
        # Если данных все еще недостаточно
        if not states:
            return {
                "aspect": aspect,
                "period_days": days,
                "trend": None,
                "data_points": 0,
                "message": "Insufficient data for trend analysis"
            }
        
        # Подготавливаем данные для анализа
        dates = []
        values = []
        
        for state in states:
            dates.append(state.timestamp)
            values.append(getattr(state, aspect))
        
        # Анализ тренда с использованием линейной регрессии
        trend_result = self._analyze_trend(dates, values)
        
        # Подготавливаем данные для отображения
        data_points = [
            {"date": date.isoformat(), "value": value}
            for date, value in zip(dates, values)
        ]
        
        result = {
            "aspect": aspect,
            "period_days": days,
            "data_points": len(values),
            "average": trend_result["average"],
            "min": trend_result["min"],
            "max": trend_result["max"],
            "trend": trend_result["trend"],
            "trend_coefficient": trend_result["coefficient"],
            "volatility": trend_result["volatility"],
            "data": data_points,
            "analysis": self._generate_trend_analysis(aspect, trend_result)
        }
        
        # Кэшируем результат
        await set_cache(cache_key, json.dumps(result), expires=3600)  # кэш на 1 час
        
        return result
        
    def _analyze_trend(self, dates: List[datetime], values: List[float]) -> Dict[str, Any]:
        """
        Вспомогательный метод для анализа тренда с использованием линейной регрессии.
        """
        # Преобразуем даты в числовые значения (дни от начальной даты)
        if not dates or not values:
            return {"trend": None, "coefficient": 0, "average": 0, "min": 0, "max": 0, "volatility": 0}
            
        start_date = dates[0]
        x = [(date - start_date).total_seconds() / 86400 for date in dates]  # дни
        y = values
        
        # Простая линейная регрессия
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x_i - mean_x) * (y_i - mean_y) for x_i, y_i in zip(x, y))
        denominator = sum((x_i - mean_x) ** 2 for x_i in x)
        
        # Защита от деления на ноль
        if denominator == 0:
            coefficient = 0
        else:
            coefficient = numerator / denominator
        
        # Определяем тренд
        if abs(coefficient) < 0.01:
            trend = "stable"
        elif coefficient > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # Рассчитываем волатильность (стандартное отклонение)
        if len(values) > 1:
            volatility = statistics.stdev(values)
        else:
            volatility = 0
            
        return {
            "trend": trend,
            "coefficient": coefficient,
            "average": mean_y,
            "min": min(y),
            "max": max(y),
            "volatility": volatility
        }
        
    def _generate_trend_analysis(self, aspect: str, trend_result: Dict[str, Any]) -> str:
        """
        Генерирует текстовый анализ тренда для заданного аспекта состояния.
        """
        # Словарь с человекопонятными названиями аспектов
        aspect_names = {
            "mood_score": "настроение",
            "energy_level": "энергия",
            "stress_level": "стресс",
            "anxiety_level": "тревожность",
            "focus_level": "концентрация",
            "motivation_level": "мотивация",
            "sleep_quality": "качество сна",
            "wellbeing_index": "индекс благополучия"
        }
        
        # Словарь с описаниями трендов
        trend_descriptions = {
            "increasing": "повышается",
            "decreasing": "снижается",
            "stable": "остается стабильным"
        }
        
        # Получаем название аспекта и описание тренда
        aspect_name = aspect_names.get(aspect, aspect)
        trend_description = trend_descriptions.get(trend_result["trend"], "меняется")
        
        # Формируем базовое описание
        analysis = f"За указанный период {aspect_name} {trend_description}."
        
        # Добавляем детали в зависимости от аспекта и тренда
        if aspect == "mood_score":
            if trend_result["trend"] == "increasing":
                analysis += " Это положительная тенденция, свидетельствующая о улучшении эмоционального состояния."
            elif trend_result["trend"] == "decreasing":
                analysis += " Следует обратить внимание на факторы, влияющие на настроение."
            else:
                analysis += f" Среднее значение настроения составляет {trend_result['average']:.1f} из диапазона от -10 до +10."
                
        elif aspect == "energy_level":
            if trend_result["trend"] == "increasing":
                analysis += " Наблюдается рост энергии, что может свидетельствовать о повышении витальности."
            elif trend_result["trend"] == "decreasing":
                analysis += " Это может указывать на накопление усталости или недостаток восстановления."
            else:
                analysis += f" Средний уровень энергии составляет {trend_result['average']:.1f} из диапазона от -10 до +10."
                
        elif aspect == "stress_level":
            if trend_result["trend"] == "increasing":
                analysis += " Рост уровня стресса требует внимания и применения техник управления стрессом."
            elif trend_result["trend"] == "decreasing":
                analysis += " Снижение уровня стресса является положительной тенденцией."
            else:
                analysis += f" Средний уровень стресса составляет {trend_result['average']:.1f} из 10."
                
        elif aspect == "wellbeing_index":
            if trend_result["trend"] == "increasing":
                analysis += " Повышение индекса благополучия отражает общее улучшение состояния."
            elif trend_result["trend"] == "decreasing":
                analysis += " Снижение индекса благополучия требует комплексного анализа его компонентов."
            else:
                analysis += f" Средний индекс благополучия составляет {trend_result['average']:.1f} из 100."
        
        # Добавляем информацию о волатильности
        if trend_result["volatility"] > 0:
            if trend_result["volatility"] < 1:
                analysis += " Показатель достаточно стабилен."
            elif trend_result["volatility"] < 3:
                analysis += " Наблюдаются умеренные колебания показателя."
            else:
                analysis += " Отмечаются значительные колебания показателя, что может свидетельствовать о нестабильности."
        
        return analysis
        
    async def detect_state_anomalies(
        self, 
        user_id: UUID, 
        threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Обнаружение аномалий в состоянии пользователя на основе статистического анализа.
        
        Параметры:
        - threshold: порог стандартного отклонения для определения аномалии
        """
        # Получаем данные за последние 30 дней
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        # Получаем данные из базы данных
        query = (
            select(UserState)
            .where(
                UserState.user_id == user_id,
                UserState.timestamp >= from_date,
                UserState.timestamp <= to_date
            )
            .order_by(UserState.timestamp)
        )
        
        result = await self.db.execute(query)
        states = result.scalars().all()
        
        # Если данных недостаточно
        if len(states) < 5:
            return []
        
        # Определяем аспекты для анализа
        aspects = [
            "mood_score", "energy_level", "stress_level", 
            "anxiety_level", "focus_level", "sleep_quality",
            "wellbeing_index"
        ]
        
        # Словарь с человекопонятными названиями аспектов
        aspect_names = {
            "mood_score": "настроение",
            "energy_level": "энергия",
            "stress_level": "стресс",
            "anxiety_level": "тревожность",
            "focus_level": "концентрация",
            "sleep_quality": "качество сна",
            "wellbeing_index": "индекс благополучия"
        }
        
        # Выявляем аномалии для каждого аспекта
        anomalies = []
        
        for aspect in aspects:
            # Собираем значения аспекта
            values = []
            dates = []
            
            for state in states:
                value = getattr(state, aspect)
                if value is not None:
                    values.append(value)
                    dates.append(state.timestamp)
            
            # Если недостаточно данных для этого аспекта
            if len(values) < 5:
                continue
            
            # Рассчитываем среднее и стандартное отклонение
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            # Выявляем аномалии
            for i, value in enumerate(values):
                # Рассчитываем Z-score
                z_score = abs(value - mean) / stdev
                
                # Если значение выходит за пределы порога
                if z_score > threshold:
                    # Определяем тип аномалии
                    if value > mean:
                        anomaly_type = "high"
                    else:
                        anomaly_type = "low"
                    
                    # Добавляем аномалию в список
                    anomalies.append({
                        "aspect": aspect,
                        "aspect_name": aspect_names.get(aspect, aspect),
                        "date": dates[i].isoformat(),
                        "value": value,
                        "mean": mean,
                        "z_score": z_score,
                        "anomaly_type": anomaly_type,
                        "severity": "high" if z_score > 3 else "medium" if z_score > 2.5 else "low"
                    })
        
        # Сортируем аномалии по дате (сначала новые)
        anomalies.sort(key=lambda x: x["date"], reverse=True)
        
        return anomalies
        
    async def get_state_history(
        self, 
        user_id: UUID, 
        aspects: List[str] = None, 
        from_date: datetime = None, 
        to_date: datetime = None
    ) -> Dict[str, List]:
        """
        Получение истории состояния пользователя за указанный период.
        
        Параметры:
        - aspects: список аспектов для получения (mood_score, energy_level и т.д.)
        - from_date: начало периода
        - to_date: конец периода
        """
        # Если аспекты не указаны, используем все основные
        if not aspects:
            aspects = [
                "mood_score", "energy_level", "stress_level", 
                "anxiety_level", "wellbeing_index"
            ]
        
        # Устанавливаем даты по умолчанию, если не указаны
        if not from_date:
            from_date = datetime.now() - timedelta(days=30)
            
        if not to_date:
            to_date = datetime.now()
            
        # Формируем ключ кэша
        aspects_key = "_".join(sorted(aspects))
        cache_key = f"state_history:{user_id}:{aspects_key}:{from_date.isoformat()}:{to_date.isoformat()}"
        
        # Проверяем кэш
        cached_history = await get_cache(cache_key)
        if cached_history:
            return json.loads(cached_history)
        
        # Получаем данные из базы данных
        query = (
            select(UserState)
            .where(
                UserState.user_id == user_id,
                UserState.timestamp >= from_date,
                UserState.timestamp <= to_date
            )
            .order_by(UserState.timestamp)
        )
        
        result = await self.db.execute(query)
        states = result.scalars().all()
        
        # Если данных из SQL недостаточно, дополняем данными из MongoDB
        if len(states) < 5:
            # Получаем снимки состояний из MongoDB
            snapshots = await self.state_snapshot_repository.get_state_snapshots(str(user_id))
            
            # Фильтруем по датам
            snapshots = [s for s in snapshots if from_date <= s.timestamp <= to_date]
            
            # Маппинг аспектов UserState на поля в MongoDB
            aspect_mapping = {
                "mood_score": "mood.score",
                "energy_level": "energy.level",
                "stress_level": "stress.level"
            }
            
            # Добавляем данные из снимков
            for snapshot in snapshots:
                # Проверяем, есть ли уже запись с такой датой
                timestamp = snapshot.timestamp
                exists = False
                for state in states:
                    if abs((state.timestamp - timestamp).total_seconds()) < 300:  # 5 минут
                        exists = True
                        break
                
                # Если записи нет, создаем временную
                if not exists:
                    state_data = {
                        "user_id": user_id,
                        "timestamp": timestamp
                    }
                    
                    # Добавляем значения для запрошенных аспектов
                    if "mood_score" in aspects and "mood" in snapshot.dict() and "score" in snapshot.mood:
                        state_data["mood_score"] = snapshot.mood["score"]
                        
                    if "energy_level" in aspects and "energy" in snapshot.dict() and "level" in snapshot.energy:
                        state_data["energy_level"] = snapshot.energy["level"]
                        
                    if "stress_level" in aspects and "stress" in snapshot.dict() and "level" in snapshot.stress:
                        state_data["stress_level"] = snapshot.stress["level"]
                    
                    # Создаем временную запись
                    temp_state = UserState(**state_data)
                    states.append(temp_state)
            
            # Сортируем по времени
            states.sort(key=lambda x: x.timestamp)
        
        # Подготавливаем результат
        result = {}
        
        for aspect in aspects:
            result[aspect] = []
            
            for state in states:
                value = getattr(state, aspect)
                if value is not None:
                    result[aspect].append({
                        "timestamp": state.timestamp.isoformat(),
                        "value": value
                    })
        
        # Кэшируем результат
        await set_cache(cache_key, json.dumps(result), expires=3600)  # кэш на 1 час
        
        return result
        
    async def calculate_activity_impact_on_state(
        self, 
        user_id: UUID, 
        activity_id: UUID
    ) -> Dict[str, float]:
        """
        Расчет влияния активности на состояние пользователя на основе исторических данных.
        Анализирует состояние до и после активности.
        
        Параметры:
        - activity_id: идентификатор активности
        """
        # Получаем данные об активности
        from sqlalchemy import Table, Column
        from app.models.activity import Activity
        
        query = select(Activity).where(Activity.id == activity_id)
        result = await self.db.execute(query)
        activity = result.scalars().first()
        
        if not activity or activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found or belongs to another user"
            )
        
        # Получаем состояния до и после активности
        before_window = activity.start_time - timedelta(hours=3)
        after_window = activity.completion_time + timedelta(hours=3) if activity.completion_time else activity.end_time + timedelta(hours=3)
        
        # Получаем состояния до активности
        query_before = (
            select(UserState)
            .where(
                UserState.user_id == user_id,
                UserState.timestamp >= before_window,
                UserState.timestamp <= activity.start_time
            )
            .order_by(UserState.timestamp.desc())
            .limit(3)
        )
        
        result_before = await self.db.execute(query_before)
        states_before = result_before.scalars().all()
        
        # Получаем состояния после активности
        query_after = (
            select(UserState)
            .where(
                UserState.user_id == user_id,
                UserState.timestamp >= activity.end_time,
                UserState.timestamp <= after_window
            )
            .order_by(UserState.timestamp)
            .limit(3)
        )
        
        result_after = await self.db.execute(query_after)
        states_after = result_after.scalars().all()
        
        # Если недостаточно данных
        if not states_before or not states_after:
            # Проверяем, есть ли оценки активности в MongoDB
            try:
                activity_evaluations = []  # Здесь можно добавить запрос к MongoDB, если есть репозиторий
                
                if activity_evaluations:
                    # Используем данные из оценок активности
                    impact = {
                        "mood_impact": 0,
                        "energy_impact": 0,
                        "stress_impact": 0
                    }
                    
                    # Подсчитываем среднее влияние
                    for eval in activity_evaluations:
                        if hasattr(eval, "energy_impact"):
                            impact["energy_impact"] += eval.energy_impact
                        if hasattr(eval, "stress_impact"):
                            impact["stress_impact"] += eval.stress_impact
                    
                    # Нормализуем
                    if len(activity_evaluations) > 0:
                        for key in impact:
                            impact[key] /= len(activity_evaluations)
                    
                    return impact
            except Exception:
                pass
                
            # Если данных все равно нет, возвращаем нулевое влияние
            return {
                "mood_impact": 0,
                "energy_impact": 0,
                "stress_impact": 0,
                "wellbeing_impact": 0
            }
        
        # Рассчитываем средние значения до и после
        aspects = ["mood_score", "energy_level", "stress_level", "wellbeing_index"]
        before_avg = {}
        after_avg = {}
        
        for aspect in aspects:
            before_values = [getattr(state, aspect) for state in states_before if getattr(state, aspect) is not None]
            after_values = [getattr(state, aspect) for state in states_after if getattr(state, aspect) is not None]
            
            if before_values:
                before_avg[aspect] = sum(before_values) / len(before_values)
            else:
                before_avg[aspect] = None
                
            if after_values:
                after_avg[aspect] = sum(after_values) / len(after_values)
            else:
                after_avg[aspect] = None
        
        # Рассчитываем влияние
        impact = {}
        
        for aspect in aspects:
            if before_avg[aspect] is not None and after_avg[aspect] is not None:
                # Для стресса инвертируем влияние (снижение стресса = положительное влияние)
                if aspect == "stress_level":
                    impact["stress_impact"] = before_avg[aspect] - after_avg[aspect]
                else:
                    impact[f"{aspect.replace('_score', '').replace('_level', '')}_impact"] = after_avg[aspect] - before_avg[aspect]
            else:
                impact[f"{aspect.replace('_score', '').replace('_level', '')}_impact"] = 0
        
        return impact
        
    async def get_wellbeing_index(self, user_id: UUID) -> float:
        """
        Расчет индекса благополучия пользователя на основе текущего состояния.
        Возвращает значение от 0 до 100.
        """
        # Получаем текущее состояние
        current_state = await self.get_current_state(user_id)
        
        # Если у текущего состояния уже рассчитан индекс благополучия
        if current_state.wellbeing_index is not None:
            return current_state.wellbeing_index
        
        # Рассчитываем индекс благополучия
        return current_state.calculate_wellbeing_index()