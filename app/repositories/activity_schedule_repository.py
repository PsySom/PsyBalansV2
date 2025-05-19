"""
Репозиторий для работы с расписанием активностей пользователей.
"""
from typing import Optional, List, Dict, Any, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, extract, between
from sqlalchemy.sql import Select
from sqlalchemy.orm import joinedload, selectinload
from uuid import UUID
from datetime import datetime, timedelta, date
import json

from app.models.calendar import ActivitySchedule, UserCalendar
from app.repositories.base_repository import BaseRepository


class ActivityScheduleRepository(BaseRepository[ActivitySchedule]):
    """
    Репозиторий для работы с расписанием активностей пользователей.
    Предоставляет методы для планирования, обновления и получения 
    запланированных активностей.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.
        
        Args:
            db_session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(db_session, ActivitySchedule)
    
    async def schedule_activity(self, schedule_data: Dict[str, Any]) -> ActivitySchedule:
        """
        Планирование новой активности в календаре.
        
        Args:
            schedule_data: Данные для создания расписания активности
            
        Returns:
            Созданное расписание активности
        """
        # Проверяем и устанавливаем продолжительность если не указана
        if "start_time" in schedule_data and "end_time" in schedule_data and "duration_minutes" not in schedule_data:
            start_time = schedule_data["start_time"]
            end_time = schedule_data["end_time"]
            duration = int((end_time - start_time).total_seconds() / 60)
            schedule_data["duration_minutes"] = duration
        
        # Создаем запись в расписании
        scheduled_activity = await self.create(schedule_data)
        return scheduled_activity
    
    async def create_recurring_activity(
        self, 
        base_data: Dict[str, Any],
        recurrence_pattern: Dict[str, Any],
        start_date: datetime,
        end_date: Optional[datetime] = None,
        occurrences: Optional[int] = None,
        max_occurrences: int = 100
    ) -> List[ActivitySchedule]:
        """
        Создание повторяющихся активностей в календаре.
        
        Args:
            base_data: Базовые данные для всех повторений
            recurrence_pattern: Паттерн повторения (frequency, interval, etc.)
            start_date: Дата начала серии повторений
            end_date: Дата окончания серии повторений (опционально)
            occurrences: Количество повторений (альтернатива end_date)
            max_occurrences: Максимальное количество повторений для предотвращения бесконечных циклов
            
        Returns:
            Список созданных записей расписания
        """
        # Валидация параметров повторения
        frequency = recurrence_pattern.get("frequency")
        if not frequency:
            raise ValueError("Frequency is required in recurrence pattern")
        
        interval = recurrence_pattern.get("interval", 1)
        weekdays = recurrence_pattern.get("weekdays", [])
        monthdays = recurrence_pattern.get("monthdays", [])
        
        # Создаем первый экземпляр активности
        base_data["start_time"] = start_date
        end_time = start_date + timedelta(minutes=base_data.get("duration_minutes", 60))
        base_data["end_time"] = end_time
        base_data["is_recurring"] = True
        base_data["recurrence_pattern"] = recurrence_pattern
        
        first_occurrence = await self.create(base_data)
        
        # Список для хранения всех созданных активностей
        schedules = [first_occurrence]
        parent_id = first_occurrence.id
        
        # Счетчик для предотвращения бесконечных циклов
        count = 1
        
        # Создаем экземпляры по шаблону
        current_date = start_date
        
        while True:
            # Условия выхода из цикла
            if occurrences and count >= occurrences:
                break
            if end_date and current_date > end_date:
                break
            if count >= max_occurrences:
                break
            
            # Вычисляем следующую дату в зависимости от частоты
            if frequency == "daily":
                current_date = current_date + timedelta(days=interval)
            elif frequency == "weekly":
                # Проверяем, есть ли указанные дни недели
                if weekdays:
                    # Если есть указанные дни недели, создаем активности для каждого дня
                    # Пропускаем первую неделю, так как она уже создана
                    if count == 1:
                        base_weekday = current_date.weekday()
                        for day in weekdays:
                            if day != base_weekday:
                                day_diff = day - base_weekday
                                if day_diff <= 0:
                                    day_diff += 7
                                occurrence_date = current_date + timedelta(days=day_diff)
                                if end_date and occurrence_date > end_date:
                                    continue
                                
                                occurrence_data = base_data.copy()
                                occurrence_data["start_time"] = occurrence_date
                                occurrence_data["end_time"] = occurrence_date + timedelta(minutes=base_data.get("duration_minutes", 60))
                                occurrence_data["recurrence_parent_id"] = parent_id
                                
                                occurrence = await self.create(occurrence_data)
                                schedules.append(occurrence)
                                count += 1
                                
                                if occurrences and count >= occurrences:
                                    break
                    
                    # Переходим к следующей неделе
                    current_date = current_date + timedelta(weeks=interval)
                else:
                    # Если нет указанных дней недели, просто добавляем недели
                    current_date = current_date + timedelta(weeks=interval)
            elif frequency == "monthly":
                # Определяем число месяца
                if monthdays:
                    # Если есть указанные дни месяца
                    current_day = current_date.day
                    month_added = False
                    
                    for day in monthdays:
                        if not month_added and day == current_day:
                            # Добавляем месяц к текущей дате
                            month = current_date.month + interval
                            year = current_date.year + (month - 1) // 12
                            month = ((month - 1) % 12) + 1
                            
                            try:
                                current_date = current_date.replace(year=year, month=month)
                            except ValueError:
                                # Если день не существует в месяце (например, 31 февраля)
                                # берем последний день месяца
                                if month == 2:
                                    current_date = current_date.replace(year=year, month=month, day=28)
                                else:
                                    current_date = current_date.replace(year=year, month=month, day=30)
                            
                            month_added = True
                        else:
                            # Создаем активность для другого дня текущего месяца
                            try:
                                occurrence_date = current_date.replace(day=day)
                                # Проверяем, что новая дата больше начальной
                                if occurrence_date <= start_date:
                                    continue
                                if end_date and occurrence_date > end_date:
                                    continue
                                
                                occurrence_data = base_data.copy()
                                occurrence_data["start_time"] = occurrence_date
                                occurrence_data["end_time"] = occurrence_date + timedelta(minutes=base_data.get("duration_minutes", 60))
                                occurrence_data["recurrence_parent_id"] = parent_id
                                
                                occurrence = await self.create(occurrence_data)
                                schedules.append(occurrence)
                                count += 1
                                
                                if occurrences and count >= occurrences:
                                    break
                            except ValueError:
                                # Если день не существует в месяце, пропускаем
                                pass
                else:
                    # Добавляем месяц к текущей дате
                    month = current_date.month + interval
                    year = current_date.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    
                    try:
                        current_date = current_date.replace(year=year, month=month)
                    except ValueError:
                        # Если день не существует в месяце (например, 31 февраля)
                        # берем последний день месяца
                        if month == 2:
                            current_date = current_date.replace(year=year, month=month, day=28)
                        else:
                            current_date = current_date.replace(year=year, month=month, day=30)
            elif frequency == "yearly":
                # Добавляем год к текущей дате
                current_date = current_date.replace(year=current_date.year + interval)
            
            # Если не ежемесячная повторяющаяся активность с указанными днями,
            # создаем следующую активность
            if not (frequency == "monthly" and monthdays) and not (frequency == "weekly" and weekdays):
                occurrence_data = base_data.copy()
                occurrence_data["start_time"] = current_date
                occurrence_data["end_time"] = current_date + timedelta(minutes=base_data.get("duration_minutes", 60))
                occurrence_data["recurrence_parent_id"] = parent_id
                
                occurrence = await self.create(occurrence_data)
                schedules.append(occurrence)
                count += 1
        
        return schedules
    
    async def mark_as_completed(
        self, 
        schedule_id: UUID, 
        completion_time: Optional[datetime] = None,
        update_data: Optional[Dict[str, Any]] = None
    ) -> Optional[ActivitySchedule]:
        """
        Отметка активности как выполненной.
        
        Args:
            schedule_id: Идентификатор запланированной активности
            completion_time: Время завершения активности (по умолчанию текущее время)
            update_data: Дополнительные данные для обновления (например, заметки, оценка)
            
        Returns:
            Обновленное расписание активности или None, если не найдено
        """
        # Получаем текущую запись расписания
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None
        
        # Устанавливаем время завершения и статус
        if not completion_time:
            completion_time = datetime.now()
        
        # Создаем словарь с обновленными данными
        update_dict = {
            "status": "completed",
            "completion_time": completion_time
        }
        
        # Добавляем дополнительные данные для обновления
        if update_data:
            update_dict.update(update_data)
        
        # Обновляем запись
        updated_schedule = await self.update(schedule_id, update_dict)
        return updated_schedule
    
    async def mark_as_in_progress(self, schedule_id: UUID) -> Optional[ActivitySchedule]:
        """
        Отметка активности как выполняемой.
        
        Args:
            schedule_id: Идентификатор запланированной активности
            
        Returns:
            Обновленное расписание активности или None, если не найдено
        """
        return await self.update(schedule_id, {"status": "in_progress"})
    
    async def mark_as_cancelled(self, schedule_id: UUID) -> Optional[ActivitySchedule]:
        """
        Отметка активности как отмененной.
        
        Args:
            schedule_id: Идентификатор запланированной активности
            
        Returns:
            Обновленное расписание активности или None, если не найдено
        """
        return await self.update(schedule_id, {"status": "cancelled"})
    
    async def postpone_activity(
        self, 
        schedule_id: UUID, 
        new_start_time: datetime,
        new_end_time: Optional[datetime] = None
    ) -> Optional[ActivitySchedule]:
        """
        Перенос активности на другое время.
        
        Args:
            schedule_id: Идентификатор запланированной активности
            new_start_time: Новое время начала
            new_end_time: Новое время окончания (опционально)
            
        Returns:
            Обновленное расписание активности или None, если не найдено
        """
        # Получаем текущую запись расписания
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None
        
        # Определяем новое время окончания
        if not new_end_time:
            duration = timedelta(minutes=schedule.duration_minutes)
            new_end_time = new_start_time + duration
        
        # Вычисляем новую продолжительность в минутах
        duration_minutes = int((new_end_time - new_start_time).total_seconds() / 60)
        
        # Обновляем запись
        update_data = {
            "status": "postponed",
            "start_time": new_start_time,
            "end_time": new_end_time,
            "duration_minutes": duration_minutes
        }
        
        updated_schedule = await self.update(schedule_id, update_data)
        return updated_schedule
    
    async def get_schedule_by_date_range(
        self, 
        user_id: UUID, 
        start_date: datetime,
        end_date: datetime,
        calendar_ids: Optional[List[UUID]] = None,
        status: Optional[str] = None,
        include_cancelled: bool = False
    ) -> List[ActivitySchedule]:
        """
        Получение расписания на указанный период.
        
        Args:
            user_id: Идентификатор пользователя
            start_date: Начало периода
            end_date: Конец периода
            calendar_ids: Список идентификаторов календарей (опционально)
            status: Фильтр по статусу (опционально)
            include_cancelled: Включать ли отмененные активности
            
        Returns:
            Список запланированных активностей
        """
        # Основные условия запроса
        conditions = [
            self.model.user_id == user_id,
            or_(
                and_(
                    self.model.start_time >= start_date,
                    self.model.start_time <= end_date
                ),
                and_(
                    self.model.end_time >= start_date,
                    self.model.end_time <= end_date
                ),
                and_(
                    self.model.start_time <= start_date,
                    self.model.end_time >= end_date
                )
            )
        ]
        
        # Фильтр по календарям
        if calendar_ids:
            conditions.append(self.model.calendar_id.in_(calendar_ids))
        
        # Фильтр по статусу
        if status:
            conditions.append(self.model.status == status)
        elif not include_cancelled:
            conditions.append(self.model.status != "cancelled")
        
        # Формирование запроса
        query = (
            select(self.model)
            .where(and_(*conditions))
            .options(joinedload(self.model.activity))
            .order_by(self.model.start_time)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_day_schedule(
        self, 
        user_id: UUID, 
        date_: Union[datetime, date],
        calendar_ids: Optional[List[UUID]] = None,
        include_cancelled: bool = False
    ) -> List[ActivitySchedule]:
        """
        Получение расписания на день.
        
        Args:
            user_id: Идентификатор пользователя
            date_: Дата
            calendar_ids: Список идентификаторов календарей (опционально)
            include_cancelled: Включать ли отмененные активности
            
        Returns:
            Список запланированных активностей на день
        """
        # Преобразуем date в datetime при необходимости
        if isinstance(date_, date) and not isinstance(date_, datetime):
            start_date = datetime.combine(date_, datetime.min.time())
        else:
            start_date = datetime.combine(date_.date(), datetime.min.time())
        
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
        
        return await self.get_schedule_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            calendar_ids=calendar_ids,
            include_cancelled=include_cancelled
        )
    
    async def get_week_schedule(
        self, 
        user_id: UUID, 
        date_: Union[datetime, date],
        calendar_ids: Optional[List[UUID]] = None,
        include_cancelled: bool = False
    ) -> List[ActivitySchedule]:
        """
        Получение расписания на неделю.
        
        Args:
            user_id: Идентификатор пользователя
            date_: Любая дата недели
            calendar_ids: Список идентификаторов календарей (опционально)
            include_cancelled: Включать ли отмененные активности
            
        Returns:
            Список запланированных активностей на неделю
        """
        # Преобразуем date в datetime при необходимости
        if isinstance(date_, date) and not isinstance(date_, datetime):
            date_obj = date_
        else:
            date_obj = date_.date()
        
        # Определяем начало недели (понедельник)
        start_date = datetime.combine(date_obj - timedelta(days=date_obj.weekday()), datetime.min.time())
        end_date = start_date + timedelta(days=7) - timedelta(seconds=1)
        
        return await self.get_schedule_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            calendar_ids=calendar_ids,
            include_cancelled=include_cancelled
        )
    
    async def get_month_schedule(
        self, 
        user_id: UUID, 
        year: int,
        month: int,
        calendar_ids: Optional[List[UUID]] = None,
        include_cancelled: bool = False
    ) -> List[ActivitySchedule]:
        """
        Получение расписания на месяц.
        
        Args:
            user_id: Идентификатор пользователя
            year: Год
            month: Месяц (1-12)
            calendar_ids: Список идентификаторов календарей (опционально)
            include_cancelled: Включать ли отмененные активности
            
        Returns:
            Список запланированных активностей на месяц
        """
        # Определяем начало и конец месяца
        start_date = datetime(year, month, 1)
        
        # Определяем последний день месяца
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        return await self.get_schedule_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            calendar_ids=calendar_ids,
            include_cancelled=include_cancelled
        )
    
    async def get_upcoming_activities(
        self, 
        user_id: UUID, 
        limit: int = 10,
        calendar_ids: Optional[List[UUID]] = None,
        skip_completed: bool = True
    ) -> List[ActivitySchedule]:
        """
        Получение предстоящих активностей пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            limit: Максимальное количество активностей
            calendar_ids: Список идентификаторов календарей (опционально)
            skip_completed: Пропускать ли выполненные активности
            
        Returns:
            Список предстоящих активностей
        """
        # Основные условия запроса
        conditions = [
            self.model.user_id == user_id,
            self.model.start_time >= datetime.now(),
            self.model.status != "cancelled"
        ]
        
        # Фильтр по календарям
        if calendar_ids:
            conditions.append(self.model.calendar_id.in_(calendar_ids))
        
        # Фильтр по статусу
        if skip_completed:
            conditions.append(self.model.status != "completed")
        
        # Формирование запроса
        query = (
            select(self.model)
            .where(and_(*conditions))
            .options(joinedload(self.model.activity))
            .order_by(self.model.start_time)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_overdue_activities(
        self, 
        user_id: UUID, 
        limit: int = 10,
        calendar_ids: Optional[List[UUID]] = None
    ) -> List[ActivitySchedule]:
        """
        Получение просроченных активностей пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            limit: Максимальное количество активностей
            calendar_ids: Список идентификаторов календарей (опционально)
            
        Returns:
            Список просроченных активностей
        """
        # Основные условия запроса
        conditions = [
            self.model.user_id == user_id,
            self.model.end_time < datetime.now(),
            self.model.status == "scheduled"
        ]
        
        # Фильтр по календарям
        if calendar_ids:
            conditions.append(self.model.calendar_id.in_(calendar_ids))
        
        # Формирование запроса
        query = (
            select(self.model)
            .where(and_(*conditions))
            .options(joinedload(self.model.activity))
            .order_by(self.model.end_time.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_current_activities(
        self, 
        user_id: UUID, 
        calendar_ids: Optional[List[UUID]] = None
    ) -> List[ActivitySchedule]:
        """
        Получение текущих (выполняемых в данный момент) активностей.
        
        Args:
            user_id: Идентификатор пользователя
            calendar_ids: Список идентификаторов календарей (опционально)
            
        Returns:
            Список текущих активностей
        """
        now = datetime.now()
        
        # Основные условия запроса
        conditions = [
            self.model.user_id == user_id,
            self.model.start_time <= now,
            self.model.end_time >= now,
            or_(
                self.model.status == "scheduled",
                self.model.status == "in_progress"
            )
        ]
        
        # Фильтр по календарям
        if calendar_ids:
            conditions.append(self.model.calendar_id.in_(calendar_ids))
        
        # Формирование запроса
        query = (
            select(self.model)
            .where(and_(*conditions))
            .options(joinedload(self.model.activity))
            .order_by(self.model.start_time)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_recurring_activities(
        self, 
        user_id: UUID,
        parent_id: Optional[UUID] = None,
        calendar_ids: Optional[List[UUID]] = None
    ) -> List[ActivitySchedule]:
        """
        Получение повторяющихся активностей пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            parent_id: Идентификатор родительской активности (опционально)
            calendar_ids: Список идентификаторов календарей (опционально)
            
        Returns:
            Список повторяющихся активностей
        """
        # Основные условия запроса
        conditions = [
            self.model.user_id == user_id,
            self.model.is_recurring == True
        ]
        
        # Фильтр по родительской активности
        if parent_id:
            conditions.append(
                or_(
                    self.model.id == parent_id,
                    self.model.recurrence_parent_id == parent_id
                )
            )
        
        # Фильтр по календарям
        if calendar_ids:
            conditions.append(self.model.calendar_id.in_(calendar_ids))
        
        # Формирование запроса
        query = (
            select(self.model)
            .where(and_(*conditions))
            .options(
                joinedload(self.model.recurring_schedules),
                joinedload(self.model.parent_schedule)
            )
            .order_by(self.model.start_time)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_activity_schedule(
        self, 
        schedule_id: UUID, 
        update_data: Dict[str, Any],
        update_recurring: bool = False
    ) -> List[ActivitySchedule]:
        """
        Обновление параметров запланированной активности.
        
        Args:
            schedule_id: Идентификатор запланированной активности
            update_data: Данные для обновления
            update_recurring: Обновлять ли все экземпляры повторяющейся активности
            
        Returns:
            Список обновленных активностей
        """
        # Получаем текущую запись расписания
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return []
        
        # Список обновленных активностей
        updated_schedules = []
        
        # Если нужно обновить все экземпляры повторяющейся активности
        if update_recurring and (schedule.is_recurring or schedule.recurrence_parent_id):
            # Определяем родительскую запись
            parent_id = schedule.recurrence_parent_id or schedule.id
            
            # Получаем все связанные активности
            related_schedules = await self.get_recurring_activities(
                user_id=schedule.user_id,
                parent_id=parent_id
            )
            
            # Обновляем все связанные активности
            for related_schedule in related_schedules:
                updated_schedule = await self.update(related_schedule.id, update_data)
                updated_schedules.append(updated_schedule)
        else:
            # Обновляем только текущую активность
            updated_schedule = await self.update(schedule_id, update_data)
            updated_schedules.append(updated_schedule)
        
        return updated_schedules
    
    async def delete_activity_schedule(
        self, 
        schedule_id: UUID,
        delete_recurring: bool = False,
        soft_delete: bool = True
    ) -> bool:
        """
        Удаление запланированной активности.
        
        Args:
            schedule_id: Идентификатор запланированной активности
            delete_recurring: Удалять ли все экземпляры повторяющейся активности
            soft_delete: Выполнять ли мягкое удаление
            
        Returns:
            True если удаление успешно, иначе False
        """
        # Получаем текущую запись расписания
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return False
        
        # Если нужно удалить все экземпляры повторяющейся активности
        if delete_recurring and (schedule.is_recurring or schedule.recurrence_parent_id):
            # Определяем родительскую запись
            parent_id = schedule.recurrence_parent_id or schedule.id
            
            # Получаем все связанные активности
            related_schedules = await self.get_recurring_activities(
                user_id=schedule.user_id,
                parent_id=parent_id
            )
            
            # Удаляем все связанные активности
            all_deleted = True
            for related_schedule in related_schedules:
                result = await self.delete(related_schedule.id, soft_delete=soft_delete)
                all_deleted = all_deleted and result
            
            return all_deleted
        else:
            # Удаляем только текущую активность
            return await self.delete(schedule_id, soft_delete=soft_delete)
    
    async def get_schedule_statistics(
        self, 
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        calendar_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Получение статистики по расписанию за период.
        
        Args:
            user_id: Идентификатор пользователя
            start_date: Начало периода
            end_date: Конец периода
            calendar_ids: Список идентификаторов календарей (опционально)
            
        Returns:
            Словарь со статистикой
        """
        # Основные условия запроса
        conditions = [
            self.model.user_id == user_id,
            or_(
                and_(
                    self.model.start_time >= start_date,
                    self.model.start_time <= end_date
                ),
                and_(
                    self.model.end_time >= start_date,
                    self.model.end_time <= end_date
                )
            )
        ]
        
        # Фильтр по календарям
        if calendar_ids:
            conditions.append(self.model.calendar_id.in_(calendar_ids))
        
        # Запрос для подсчета количества активностей по статусам
        status_counts_query = (
            select(
                self.model.status,
                func.count(self.model.id).label("count")
            )
            .where(and_(*conditions))
            .group_by(self.model.status)
        )
        
        # Запрос для подсчета общей продолжительности активностей
        duration_query = (
            select(func.sum(self.model.duration_minutes))
            .where(and_(*conditions))
        )
        
        # Запрос для подсчета количества активностей по календарям
        calendar_counts_query = (
            select(
                self.model.calendar_id,
                func.count(self.model.id).label("count")
            )
            .where(and_(*conditions))
            .group_by(self.model.calendar_id)
        )
        
        # Выполнение запросов
        status_counts_result = await self.db.execute(status_counts_query)
        duration_result = await self.db.execute(duration_query)
        calendar_counts_result = await self.db.execute(calendar_counts_query)
        
        # Получение календарей для добавления имен
        calendar_ids_from_stats = [row[0] for row in calendar_counts_result.all()]
        calendar_counts_result = await self.db.execute(calendar_counts_query)
        
        calendars_query = (
            select(UserCalendar)
            .where(UserCalendar.id.in_(calendar_ids_from_stats))
        )
        calendars_result = await self.db.execute(calendars_query)
        calendars = {cal.id: cal.name for cal in calendars_result.scalars().all()}
        
        # Формирование результата
        status_counts = {row[0]: row[1] for row in status_counts_result.all()}
        total_duration = duration_result.scalar() or 0
        calendar_counts = {
            calendars.get(row[0], str(row[0])): row[1] 
            for row in calendar_counts_result.all()
        }
        
        return {
            "total_activities": sum(status_counts.values()),
            "status_counts": status_counts,
            "total_duration_minutes": total_duration,
            "calendar_counts": calendar_counts,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }