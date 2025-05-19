"""
Репозиторий для работы со шкалами самонаблюдения.
Предоставляет методы для управления шкалами и анализа оценок пользователей.
"""
from typing import List, Optional, Dict, Any, Union, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, extract, between, desc
from uuid import UUID
from datetime import datetime, timedelta, date

from app.models.user_state import ObservationScale, ScaleCategory, ScaleRating
from app.repositories.base_repository import BaseRepository


class ScaleRepository(BaseRepository[ObservationScale]):
    """
    Репозиторий для работы со шкалами самонаблюдения.
    Предоставляет методы для получения, создания и анализа шкал оценки.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.
        
        Args:
            db_session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(db_session, ObservationScale)
    
    async def get_available_scales(
        self, 
        user_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        include_inactive: bool = False,
        include_system: bool = True
    ) -> List[ObservationScale]:
        """
        Получение доступных шкал оценки с возможностью фильтрации.
        
        Args:
            user_id: Идентификатор пользователя для получения пользовательских шкал
            category_id: Идентификатор категории для фильтрации
            include_inactive: Включать ли неактивные шкалы
            include_system: Включать ли системные шкалы
            
        Returns:
            Список доступных шкал
        """
        # Формируем базовые условия запроса
        conditions = []
        
        # Фильтр по активности
        if not include_inactive:
            conditions.append(ObservationScale.is_active == True)
        
        # Формируем условие для выбора системных и/или пользовательских шкал
        if user_id is not None:
            # Показываем системные шкалы и пользовательские шкалы этого пользователя
            if include_system:
                conditions.append(
                    or_(
                        ObservationScale.is_system == True,
                        ObservationScale.creator_id == user_id
                    )
                )
            else:
                # Показываем только пользовательские шкалы этого пользователя
                conditions.append(ObservationScale.creator_id == user_id)
        else:
            # Если пользователь не указан, фильтруем только по is_system
            if not include_system:
                conditions.append(ObservationScale.is_system == False)
        
        # Создаем и выполняем запрос
        query = select(ObservationScale)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Если указана категория, добавляем фильтр
        if category_id:
            # Для фильтрации по категории используем подзапрос
            query = query.join(ScaleCategory.scales).where(ScaleCategory.id == category_id)
        
        # Добавляем сортировку
        query = query.order_by(ObservationScale.is_system.desc(), ObservationScale.name.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_scale_categories(
        self, 
        include_empty: bool = False,
        include_system: bool = True,
        user_id: Optional[UUID] = None
    ) -> List[ScaleCategory]:
        """
        Получение категорий шкал.
        
        Args:
            include_empty: Включать ли категории без шкал
            include_system: Включать ли системные категории
            user_id: Идентификатор пользователя для пользовательских категорий
            
        Returns:
            Список категорий
        """
        # Формируем базовые условия запроса
        conditions = []
        
        # Фильтр по системным/пользовательским категориям
        if user_id is not None:
            if include_system:
                # Показываем системные категории и категории пользователя
                conditions.append(
                    or_(
                        ScaleCategory.is_system == True,
                        ScaleCategory.created_by == user_id
                    )
                )
            else:
                # Показываем только категории пользователя
                conditions.append(ScaleCategory.created_by == user_id)
        elif not include_system:
            # Если не включаем системные и пользователь не указан
            conditions.append(ScaleCategory.is_system == False)
        
        # Создаем запрос
        query = select(ScaleCategory)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Если не включаем пустые категории, добавляем условие
        if not include_empty:
            query = query.join(ObservationScale.categories).group_by(ScaleCategory.id).having(func.count(ObservationScale.id) > 0)
        
        # Добавляем сортировку
        query = query.order_by(ScaleCategory.order.asc(), ScaleCategory.name.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_scale_rating(
        self, 
        user_id: UUID, 
        scale_id: UUID, 
        value: float,
        timestamp: Optional[datetime] = None,
        activity_id: Optional[UUID] = None,
        activity_schedule_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScaleRating:
        """
        Сохранение оценки пользователя по шкале.
        
        Args:
            user_id: Идентификатор пользователя
            scale_id: Идентификатор шкалы
            value: Значение оценки
            timestamp: Временная метка оценки (по умолчанию текущее время)
            activity_id: Идентификатор связанной активности (опционально)
            activity_schedule_id: Идентификатор записи расписания (опционально)
            notes: Заметки к оценке (опционально)
            context: Контекст оценки в формате JSON (опционально)
            
        Returns:
            Созданная запись оценки
        """
        # Проверяем существование шкалы и допустимость значения
        scale = await self.get_by_id(scale_id)
        if not scale:
            raise ValueError(f"Шкала с ID {scale_id} не найдена")
        
        # Проверяем допустимость значения оценки
        if value < scale.min_value or value > scale.max_value:
            raise ValueError(
                f"Значение {value} выходит за допустимые пределы шкалы ({scale.min_value} - {scale.max_value})"
            )
        
        # Создаем данные для записи
        rating_data = {
            "user_id": user_id,
            "scale_id": scale_id,
            "value": value,
            "timestamp": timestamp or datetime.now(),
            "notes": notes,
            "context": context
        }
        
        # Добавляем связи с активностью, если указаны
        if activity_id:
            rating_data["activity_id"] = activity_id
        if activity_schedule_id:
            rating_data["activity_schedule_id"] = activity_schedule_id
        
        # Создаем запись в репозитории
        scale_rating_repository = ScaleRatingRepository(self.db)
        return await scale_rating_repository.create(rating_data)
    
    async def create_custom_scale(
        self, 
        user_id: UUID,
        name: str,
        min_value: float,
        max_value: float,
        description: Optional[str] = None,
        step: float = 1.0,
        default_value: Optional[float] = None,
        display_type: str = "slider",
        is_inverted: bool = False,
        labels: Optional[Dict[str, str]] = None,
        category_ids: Optional[List[UUID]] = None
    ) -> ObservationScale:
        """
        Создание пользовательской шкалы.
        
        Args:
            user_id: Идентификатор пользователя-создателя
            name: Название шкалы
            min_value: Минимальное значение шкалы
            max_value: Максимальное значение шкалы
            description: Описание шкалы (опционально)
            step: Шаг шкалы (опционально)
            default_value: Значение по умолчанию (опционально)
            display_type: Тип отображения (slider, buttons, etc.)
            is_inverted: Инвертированная ли шкала (выше=хуже)
            labels: Метки для значений шкалы (опционально)
            category_ids: Список ID категорий (опционально)
            
        Returns:
            Созданная шкала
        """
        # Проверка корректности параметров
        if min_value >= max_value:
            raise ValueError("Минимальное значение должно быть меньше максимального")
        
        if default_value is not None and (default_value < min_value or default_value > max_value):
            raise ValueError("Значение по умолчанию должно быть в пределах шкалы")
        
        # Создаем данные для шкалы
        scale_data = {
            "name": name,
            "description": description,
            "min_value": min_value,
            "max_value": max_value,
            "step": step,
            "default_value": default_value,
            "display_type": display_type,
            "is_inverted": is_inverted,
            "labels": labels,
            "is_system": False,
            "creator_id": user_id,
            "is_active": True
        }
        
        # Создаем шкалу
        scale = await self.create(scale_data)
        
        # Если указаны категории, добавляем их
        if category_ids and scale.id:
            # Проверяем существование категорий
            for category_id in category_ids:
                query = select(ScaleCategory).where(ScaleCategory.id == category_id)
                result = await self.db.execute(query)
                category = result.scalars().first()
                
                if category:
                    # Добавляем связь шкалы с категорией
                    insert_stmt = scale_categories.insert().values(
                        scale_id=scale.id,
                        category_id=category_id
                    )
                    await self.db.execute(insert_stmt)
            
            # Обновляем объект шкалы после изменений
            await self.db.refresh(scale)
        
        return scale


class ScaleRatingRepository(BaseRepository[ScaleRating]):
    """
    Репозиторий для работы с оценками по шкалам.
    Предоставляет методы для получения и анализа оценок пользователей.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.
        
        Args:
            db_session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(db_session, ScaleRating)
    
    async def get_user_ratings(
        self,
        user_id: UUID,
        scale_id: Optional[UUID] = None,
        activity_id: Optional[UUID] = None,
        activity_schedule_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ScaleRating]:
        """
        Получение оценок пользователя по шкалам.
        
        Args:
            user_id: Идентификатор пользователя
            scale_id: Идентификатор шкалы для фильтрации (опционально)
            activity_id: Идентификатор активности для фильтрации (опционально)
            activity_schedule_id: Идентификатор расписания для фильтрации (опционально)
            start_date: Начало периода (опционально)
            end_date: Конец периода (опционально)
            limit: Максимальное количество результатов
            
        Returns:
            Список оценок пользователя
        """
        # Формируем базовые условия запроса
        conditions = [ScaleRating.user_id == user_id]
        
        # Добавляем фильтры, если они указаны
        if scale_id:
            conditions.append(ScaleRating.scale_id == scale_id)
        if activity_id:
            conditions.append(ScaleRating.activity_id == activity_id)
        if activity_schedule_id:
            conditions.append(ScaleRating.activity_schedule_id == activity_schedule_id)
        
        # Добавляем фильтры по датам
        if start_date:
            conditions.append(ScaleRating.timestamp >= start_date)
        if end_date:
            conditions.append(ScaleRating.timestamp <= end_date)
        
        # Создаем запрос
        query = (
            select(ScaleRating)
            .where(and_(*conditions))
            .order_by(desc(ScaleRating.timestamp))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def analyze_scale_dynamics(
        self,
        user_id: UUID,
        scale_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "day"  # 'day', 'week', 'month'
    ) -> Dict[str, Any]:
        """
        Анализ динамики показателей по шкале.
        
        Args:
            user_id: Идентификатор пользователя
            scale_id: Идентификатор шкалы
            start_date: Начало периода (если не указано, используется -30 дней от end_date)
            end_date: Конец периода (если не указано, используется текущее время)
            interval: Интервал агрегации ('day', 'week', 'month')
            
        Returns:
            Словарь с результатами анализа
        """
        # Устанавливаем значения по умолчанию для дат
        if end_date is None:
            end_date = datetime.now()
        
        if start_date is None:
            if interval == "day":
                start_date = end_date - timedelta(days=30)
            elif interval == "week":
                start_date = end_date - timedelta(days=90)
            else:  # month
                start_date = end_date - timedelta(days=365)
        
        # Проверяем существование шкалы
        scale = await self.db.execute(select(ObservationScale).where(ObservationScale.id == scale_id))
        scale = scale.scalars().first()
        
        if not scale:
            raise ValueError(f"Шкала с ID {scale_id} не найдена")
        
        # Получаем все оценки пользователя за период
        conditions = [
            ScaleRating.user_id == user_id,
            ScaleRating.scale_id == scale_id,
            ScaleRating.timestamp >= start_date,
            ScaleRating.timestamp <= end_date
        ]
        
        query = select(ScaleRating).where(and_(*conditions)).order_by(ScaleRating.timestamp)
        result = await self.db.execute(query)
        ratings = result.scalars().all()
        
        # Если нет данных, возвращаем пустой результат
        if not ratings:
            return {
                "scale_id": str(scale_id),
                "scale_name": scale.name,
                "user_id": str(user_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "interval": interval,
                "points": [],
                "total_points": 0,
                "average": None,
                "min_value": None,
                "max_value": None,
                "trend": None
            }
        
        # Агрегируем данные по интервалам
        aggregated_data = {}
        
        for rating in ratings:
            # Определяем ключ для интервала
            if interval == "day":
                interval_key = rating.timestamp.date().isoformat()
            elif interval == "week":
                # Находим начало недели (понедельник)
                week_start = rating.timestamp.date() - timedelta(days=rating.timestamp.weekday())
                interval_key = week_start.isoformat()
            else:  # month
                interval_key = f"{rating.timestamp.year}-{rating.timestamp.month:02d}"
            
            # Добавляем значение в агрегированные данные
            if interval_key not in aggregated_data:
                aggregated_data[interval_key] = {
                    "values": [rating.value],
                    "timestamp": rating.timestamp
                }
            else:
                aggregated_data[interval_key]["values"].append(rating.value)
                # Обновляем timestamp, если текущий более поздний
                if rating.timestamp > aggregated_data[interval_key]["timestamp"]:
                    aggregated_data[interval_key]["timestamp"] = rating.timestamp
        
        # Вычисляем статистики для каждого интервала
        points = []
        all_values = []
        
        for interval_key, data in sorted(aggregated_data.items()):
            values = data["values"]
            avg_value = sum(values) / len(values)
            min_value = min(values)
            max_value = max(values)
            
            points.append({
                "interval": interval_key,
                "avg_value": avg_value,
                "min_value": min_value,
                "max_value": max_value,
                "count": len(values),
                "timestamp": data["timestamp"].isoformat()
            })
            
            all_values.extend(values)
        
        # Вычисляем общие статистики
        average = sum(all_values) / len(all_values) if all_values else None
        min_value = min(all_values) if all_values else None
        max_value = max(all_values) if all_values else None
        
        # Определяем тренд (простая линейная регрессия)
        if len(points) > 1:
            x = list(range(len(points)))
            y = [point["avg_value"] for point in points]
            
            # Рассчитываем коэффициент наклона (упрощенно)
            n = len(x)
            mean_x = sum(x) / n
            mean_y = sum(y) / n
            
            numerator = sum((x_i - mean_x) * (y_i - mean_y) for x_i, y_i in zip(x, y))
            denominator = sum((x_i - mean_x) ** 2 for x_i in x)
            
            if denominator != 0:
                slope = numerator / denominator
                if abs(slope) < 0.01:
                    trend = "stable"
                elif slope > 0:
                    trend = "increasing"
                else:
                    trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = None
        
        # Формируем результат
        return {
            "scale_id": str(scale_id),
            "scale_name": scale.name,
            "user_id": str(user_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "interval": interval,
            "points": points,
            "total_points": len(all_values),
            "average": average,
            "min_value": min_value,
            "max_value": max_value,
            "trend": trend
        }
    
    async def get_average_by_period(
        self,
        user_id: UUID,
        scale_ids: List[UUID],
        period_type: str,  # 'day', 'week', 'month'
        date: Union[datetime, date] = None
    ) -> Dict[str, Any]:
        """
        Получение средних показателей по шкалам за период.
        
        Args:
            user_id: Идентификатор пользователя
            scale_ids: Список идентификаторов шкал
            period_type: Тип периода ('day', 'week', 'month')
            date: Дата/время для определения периода (если не указано, используется текущая дата)
            
        Returns:
            Словарь с результатами агрегации
        """
        # Устанавливаем значение по умолчанию для даты
        if date is None:
            now = datetime.now()
            if isinstance(now, datetime):
                date = now.date()
            else:
                date = now
        elif isinstance(date, datetime):
            date = date.date()
        
        # Определяем начало и конец периода
        if period_type == "day":
            start_date = datetime.combine(date, datetime.min.time())
            end_date = datetime.combine(date, datetime.max.time())
        elif period_type == "week":
            # Находим начало недели (понедельник)
            week_start = date - timedelta(days=date.weekday())
            start_date = datetime.combine(week_start, datetime.min.time())
            end_date = datetime.combine(week_start + timedelta(days=6), datetime.max.time())
        elif period_type == "month":
            # Находим первый день месяца
            month_start = date.replace(day=1)
            # Находим последний день месяца
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            month_end = next_month - timedelta(days=1)
            
            start_date = datetime.combine(month_start, datetime.min.time())
            end_date = datetime.combine(month_end, datetime.max.time())
        else:
            raise ValueError(f"Неизвестный тип периода: {period_type}")
        
        # Получаем данные по шкалам
        results = {}
        
        for scale_id in scale_ids:
            # Проверяем существование шкалы
            scale = await self.db.execute(select(ObservationScale).where(ObservationScale.id == scale_id))
            scale = scale.scalars().first()
            
            if not scale:
                # Пропускаем несуществующие шкалы
                continue
            
            # Получаем оценки для шкалы за период
            conditions = [
                ScaleRating.user_id == user_id,
                ScaleRating.scale_id == scale_id,
                ScaleRating.timestamp >= start_date,
                ScaleRating.timestamp <= end_date
            ]
            
            query = select(ScaleRating).where(and_(*conditions)).order_by(ScaleRating.timestamp)
            result = await self.db.execute(query)
            ratings = result.scalars().all()
            
            # Если есть оценки, вычисляем средние значения
            if ratings:
                values = [rating.value for rating in ratings]
                avg_value = sum(values) / len(values)
                min_value = min(values)
                max_value = max(values)
                
                results[str(scale_id)] = {
                    "scale_id": str(scale_id),
                    "scale_name": scale.name,
                    "avg_value": avg_value,
                    "min_value": min_value,
                    "max_value": max_value,
                    "count": len(values)
                }
            else:
                results[str(scale_id)] = {
                    "scale_id": str(scale_id),
                    "scale_name": scale.name,
                    "avg_value": None,
                    "min_value": None,
                    "max_value": None,
                    "count": 0
                }
        
        return {
            "user_id": str(user_id),
            "period_type": period_type,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "scales": results
        }
    
    async def get_activity_impact_on_scales(
        self,
        user_id: UUID,
        activity_id: UUID,
        scale_ids: Optional[List[UUID]] = None,
        lookback_days: int = 90
    ) -> Dict[str, Any]:
        """
        Анализ влияния активности на показатели по шкалам.
        Сравнивает средние значения до и после выполнения активности.
        
        Args:
            user_id: Идентификатор пользователя
            activity_id: Идентификатор активности
            scale_ids: Список идентификаторов шкал (если не указано, используются все шкалы с оценками)
            lookback_days: Количество дней для анализа
            
        Returns:
            Словарь с результатами анализа влияния
        """
        from app.models.activity import Activity
        
        # Получаем информацию об активности
        activity_query = select(Activity).where(Activity.id == activity_id)
        activity_result = await self.db.execute(activity_query)
        activity = activity_result.scalars().first()
        
        if not activity or activity.user_id != user_id:
            raise ValueError(f"Активность с ID {activity_id} не найдена или принадлежит другому пользователю")
        
        # Определяем период анализа
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Получаем список выполнений активности за период
        conditions = [
            ScaleRating.user_id == user_id,
            ScaleRating.activity_id == activity_id,
            ScaleRating.timestamp >= start_date,
            ScaleRating.timestamp <= end_date
        ]
        
        if scale_ids:
            conditions.append(ScaleRating.scale_id.in_(scale_ids))
        
        # Получаем все оценки с этой активностью
        query = select(ScaleRating).where(and_(*conditions))
        result = await self.db.execute(query)
        activity_ratings = result.scalars().all()
        
        # Если не указаны scale_ids, определяем их из найденных оценок
        if not scale_ids and activity_ratings:
            scale_ids = list(set(rating.scale_id for rating in activity_ratings))
        
        # Если нет данных или шкал, возвращаем пустой результат
        if not scale_ids:
            return {
                "activity_id": str(activity_id),
                "activity_name": activity.name,
                "user_id": str(user_id),
                "impact": {},
                "message": "Нет данных для анализа"
            }
        
        # Анализируем влияние на каждую шкалу
        impact_results = {}
        
        for scale_id in scale_ids:
            # Получаем информацию о шкале
            scale_query = select(ObservationScale).where(ObservationScale.id == scale_id)
            scale_result = await self.db.execute(scale_query)
            scale = scale_result.scalars().first()
            
            if not scale:
                continue
            
            # Получаем все оценки по шкале за период
            scale_conditions = [
                ScaleRating.user_id == user_id,
                ScaleRating.scale_id == scale_id,
                ScaleRating.timestamp >= start_date,
                ScaleRating.timestamp <= end_date
            ]
            
            scale_query = select(ScaleRating).where(and_(*scale_conditions)).order_by(ScaleRating.timestamp)
            scale_result = await self.db.execute(scale_query)
            all_ratings = scale_result.scalars().all()
            
            # Получаем оценки с этой активностью
            activity_scale_ratings = [r for r in activity_ratings if r.scale_id == scale_id]
            
            # Если мало данных, переходим к следующей шкале
            if len(activity_scale_ratings) < 2 or len(all_ratings) < 5:
                impact_results[str(scale_id)] = {
                    "scale_id": str(scale_id),
                    "scale_name": scale.name,
                    "impact": None,
                    "confidence": 0,
                    "baseline": None,
                    "with_activity": None,
                    "sample_size": len(activity_scale_ratings),
                    "message": "Недостаточно данных для анализа"
                }
                continue
            
            # Разделяем оценки на "до/без активности" и "после/с активностью"
            # (упрощённый подход - берём оценки с активностью и без)
            with_activity_values = [r.value for r in activity_scale_ratings]
            baseline_values = [r.value for r in all_ratings if r.activity_id != activity_id]
            
            # Если есть достаточно данных, вычисляем статистики
            if baseline_values and with_activity_values:
                baseline_avg = sum(baseline_values) / len(baseline_values)
                with_activity_avg = sum(with_activity_values) / len(with_activity_values)
                
                # Вычисляем влияние
                impact = with_activity_avg - baseline_avg
                
                # Определяем уверенность в результате (упрощенно)
                # Чем больше выборка, тем выше уверенность
                confidence = min(1.0, (len(with_activity_values) / 10) * (len(baseline_values) / 20))
                
                # Для инвертированных шкал (где меньше = лучше) инвертируем знак влияния
                if scale.is_inverted:
                    impact = -impact
                
                impact_results[str(scale_id)] = {
                    "scale_id": str(scale_id),
                    "scale_name": scale.name,
                    "impact": impact,
                    "confidence": confidence,
                    "baseline": baseline_avg,
                    "with_activity": with_activity_avg,
                    "sample_size": len(with_activity_values),
                    "baseline_sample_size": len(baseline_values)
                }
            else:
                impact_results[str(scale_id)] = {
                    "scale_id": str(scale_id),
                    "scale_name": scale.name,
                    "impact": None,
                    "confidence": 0,
                    "baseline": None,
                    "with_activity": None,
                    "sample_size": len(with_activity_values),
                    "message": "Недостаточно данных для сравнения"
                }
        
        # Формируем общий результат
        return {
            "activity_id": str(activity_id),
            "activity_name": activity.name,
            "user_id": str(user_id),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": lookback_days
            },
            "impact": impact_results
        }