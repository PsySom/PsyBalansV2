"""
Сервис для работы с рекомендациями.
Реализует бизнес-логику для генерации персонализированных рекомендаций,
оценки их эффективности и адаптации к потребностям пользователя.
"""
from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import json
import random
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.orm import joinedload

from app.models.activity import Activity
from app.models.exercises import Exercise
from app.models.user_state import UserState
from app.mongodb.recommendations_diary_repository import RecommendationRepository
from app.mongodb.recommendations_diary_schemas_pydantic import (
    Recommendation, RecommendationCreate, RecommendationResponse, EffectivenessData
)
from app.services.activity_service import ActivityService
from app.services.need_service import NeedService
from app.services.state_service import StateService
from app.core.database.redis_client import get_cache, set_cache, invalidate_cache


class RecommendationService:
    """Сервис для работы с рекомендациями"""
    
    def __init__(
        self, 
        db: AsyncSession,
        recommendation_repository=None, 
        activity_service=None, 
        need_service=None, 
        state_service=None, 
        user_service=None, 
        exercise_repository=None
    ):
        self.db = db
        self.recommendation_repository = recommendation_repository or RecommendationRepository()
        self.activity_service = activity_service or ActivityService(db)
        self.need_service = need_service or NeedService(db)
        self.state_service = state_service or StateService(db)
        self.user_service = user_service
        self.exercise_repository = exercise_repository
    
    async def generate_recommendations(
        self, 
        user_id: UUID, 
        context: dict = None
    ) -> List[Recommendation]:
        """
        Генерация персонализированных рекомендаций на основе текущего состояния пользователя,
        его предпочтений, истории активностей и потребностей.
        
        Параметры:
        - context: дополнительный контекст для генерации рекомендаций (например, триггер рекомендации, приоритет и т.д.)
        """
        # Устанавливаем контекст по умолчанию, если не передан
        if not context:
            context = {
                "trigger_type": "user_request",
                "priority_level": 3
            }
            
        # Получаем текущее состояние пользователя
        current_state = await self.state_service.get_current_state(user_id)
        
        # Идентификаторы нуждающихся в удовлетворении потребностей
        need_ids = []
        
        # Получаем потребности, требующие внимания (с низким уровнем удовлетворенности)
        needs_requiring_attention = await self.need_service.get_needs_requiring_attention(user_id, threshold=-2.0)
        if needs_requiring_attention:
            need_ids = [str(need.need_id) for need in needs_requiring_attention]
        
        # Получаем рекомендации для удовлетворения выявленных потребностей
        recommendations = await self.get_recommendations_for_needs(user_id, need_ids)
        
        # Если не удалось сгенерировать рекомендации на основе потребностей,
        # получаем рекомендации на основе текущего состояния
        if not recommendations:
            # Определяем целевое состояние
            target_state = {
                "mood_score": min(current_state.mood_score + 2 if current_state.mood_score is not None else 5, 10),
                "energy_level": min(current_state.energy_level + 2 if current_state.energy_level is not None else 5, 10),
                "stress_level": max(current_state.stress_level - 2 if current_state.stress_level is not None else 3, 0)
            }
            
            recommendations = await self.get_recommendations_for_state(user_id, target_state)
        
        # Если все еще нет рекомендаций, предлагаем общие рекомендации
        if not recommendations:
            # Получаем список активностей пользователя с высокой оценкой
            query = (
                select(Activity)
                .where(
                    Activity.user_id == user_id,
                    Activity.user_rating >= 4
                )
                .order_by(func.random())
                .limit(3)
            )
            
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            # Получаем список упражнений для улучшения общего благополучия
            if self.exercise_repository:
                exercises = await self.exercise_repository.get_recommended_exercises(
                    categories=["relaxation", "mood_improvement", "energy_boost"],
                    limit=2
                )
            else:
                exercises = []
            
            # Формируем рекомендации
            recommendation_items = []
            
            # Добавляем активности
            for activity in activities:
                recommendation_items.append({
                    "item_id": str(activity.id),
                    "item_type": "activity",
                    "relevance_score": 0.7,
                    "explanation": "Эта активность ранее вызывала положительные эмоции"
                })
            
            # Добавляем упражнения
            for exercise in exercises:
                recommendation_items.append({
                    "item_id": str(exercise.id),
                    "item_type": "exercise",
                    "relevance_score": 0.6,
                    "explanation": f"Это упражнение помогает в категории {exercise.category}"
                })
            
            # Создаем рекомендацию
            if recommendation_items:
                recommendation = RecommendationCreate(
                    user_id=str(user_id),
                    timestamp=datetime.now(),
                    context=context,
                    recommendation_type="activity",
                    recommended_items=recommendation_items
                )
                
                # Сохраняем рекомендацию
                recommendation_id = await self.recommendation_repository.create_recommendation(recommendation)
                
                # Получаем созданную рекомендацию
                recommendations = [await self.recommendation_repository.get_recommendation(recommendation_id)]
        
        return recommendations
    
    async def get_recommendations_for_needs(
        self, 
        user_id: UUID, 
        need_ids: List[UUID] = None
    ) -> List[Recommendation]:
        """
        Получение рекомендаций для удовлетворения конкретных потребностей.
        
        Параметры:
        - need_ids: список идентификаторов потребностей
        """
        # Если список потребностей пуст, возвращаем пустой список
        if not need_ids:
            return []
            
        # Формируем ключ кэша
        needs_key = "_".join(sorted([str(need_id) for need_id in need_ids]))
        cache_key = f"need_recommendations:{user_id}:{needs_key}"
        
        # Проверяем кэш
        cached_recommendations = await get_cache(cache_key)
        if cached_recommendations:
            return [Recommendation.parse_obj(item) for item in json.loads(cached_recommendations)]
        
        # Получаем активности, связанные с указанными потребностями
        need_activities = []
        relevance_scores = {}
        explanations = {}
        
        # Для каждой потребности получаем связанные активности
        for need_id in need_ids:
            # Получаем все активности пользователя, связанные с этой потребностью
            query = (
                select(Activity)
                .join(Activity.activity_needs)
                .where(
                    Activity.user_id == user_id,
                    Activity.activity_needs.any(need_id=need_id),
                    Activity.is_active == True
                )
                .order_by(Activity.user_rating.desc())
            )
            
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            for activity in activities:
                # Добавляем активность в список, если ее еще нет
                if activity.id not in [act.id for act in need_activities]:
                    need_activities.append(activity)
                
                # Получаем потребность
                need = await self.need_service.need_repository.get_by_id_with_category(need_id)
                if need:
                    # Получаем связь между активностью и потребностью
                    need_links = await self.activity_service.activity_repository.get_need_links(activity.id)
                    for link in need_links:
                        if link.need_id == need_id:
                            # Рассчитываем релевантность
                            relevance = min(link.impact_level / 5.0, 1.0) if link.impact_level else 0.5
                            relevance_scores[activity.id] = max(relevance_scores.get(activity.id, 0), relevance)
                            
                            # Формируем объяснение
                            explanation = f"Эта активность помогает удовлетворить потребность в {need.name}"
                            explanations[activity.id] = explanation
                            break
        
        # Получаем упражнения для указанных потребностей
        exercises = []
        if self.exercise_repository:
            categories = []
            for need_id in need_ids:
                need = await self.need_service.need_repository.get_by_id_with_category(need_id)
                if need and need.category:
                    category = need.category.name.lower()
                    if category == "physical":
                        categories.extend(["physical_health", "energy_boost"])
                    elif category == "emotional":
                        categories.extend(["emotion_regulation", "stress_reduction"])
                    elif category == "cognitive":
                        categories.extend(["focus_improvement", "cognitive_stimulation"])
                    elif category == "social":
                        categories.extend(["connection", "communication"])
                    elif category == "spiritual":
                        categories.extend(["mindfulness", "reflection"])
            
            if categories:
                exercises = await self.exercise_repository.get_recommended_exercises(
                    categories=categories,
                    limit=3
                )
        
        # Формируем рекомендации
        recommendation_items = []
        
        # Добавляем активности (не более 3)
        for activity in need_activities[:3]:
            recommendation_items.append({
                "item_id": str(activity.id),
                "item_type": "activity",
                "relevance_score": relevance_scores.get(activity.id, 0.5),
                "explanation": explanations.get(activity.id, "Эта активность связана с вашими потребностями")
            })
        
        # Добавляем упражнения
        for exercise in exercises:
            recommendation_items.append({
                "item_id": str(exercise.id),
                "item_type": "exercise",
                "relevance_score": 0.8,
                "explanation": f"Это упражнение помогает в категории {exercise.category}"
            })
        
        # Создаем рекомендацию
        if recommendation_items:
            recommendation = RecommendationCreate(
                user_id=str(user_id),
                timestamp=datetime.now(),
                context={
                    "trigger_type": "need_deficit",
                    "priority_level": 4
                },
                recommendation_type="need_satisfaction",
                recommended_items=recommendation_items
            )
            
            # Сохраняем рекомендацию
            recommendation_id = await self.recommendation_repository.create_recommendation(recommendation)
            
            # Получаем созданную рекомендацию
            recommendation = await self.recommendation_repository.get_recommendation(recommendation_id)
            
            # Кэшируем результат
            await set_cache(cache_key, json.dumps([recommendation.dict()]), expires=1800)  # кэш на 30 минут
            
            return [recommendation]
        
        return []
    
    async def get_recommendations_for_state(
        self, 
        user_id: UUID, 
        target_state: dict
    ) -> List[Recommendation]:
        """
        Получение рекомендаций для достижения целевого состояния.
        
        Параметры:
        - target_state: целевое состояние (словарь с ключами mood_score, energy_level, stress_level и т.д.)
        """
        # Получаем текущее состояние пользователя
        current_state = await self.state_service.get_current_state(user_id)
        
        # Определяем аспекты, которые требуют улучшения
        aspects_to_improve = {}
        for aspect, target_value in target_state.items():
            current_value = getattr(current_state, aspect, None)
            if current_value is not None:
                # Для аспектов, где ниже = лучше (например, stress_level)
                if aspect == "stress_level" or aspect == "anxiety_level":
                    if current_value > target_value:
                        aspects_to_improve[aspect] = {
                            "current": current_value,
                            "target": target_value,
                            "gap": current_value - target_value
                        }
                else:
                    if current_value < target_value:
                        aspects_to_improve[aspect] = {
                            "current": current_value,
                            "target": target_value,
                            "gap": target_value - current_value
                        }
        
        # Если нет аспектов, требующих улучшения
        if not aspects_to_improve:
            return []
            
        # Формируем ключ кэша на основе аспектов, требующих улучшения
        aspects_key = "_".join([f"{aspect}:{gap['gap']:.1f}" for aspect, gap in aspects_to_improve.items()])
        cache_key = f"state_recommendations:{user_id}:{aspects_key}"
        
        # Проверяем кэш
        cached_recommendations = await get_cache(cache_key)
        if cached_recommendations:
            return [Recommendation.parse_obj(item) for item in json.loads(cached_recommendations)]
        
        # Получаем оценки выполненных активностей с их влиянием на состояние
        activity_impacts = {}
        
        # Получаем последние завершенные активности пользователя
        query = (
            select(Activity)
            .where(
                Activity.user_id == user_id,
                Activity.is_completed == True
            )
            .order_by(Activity.completion_time.desc())
            .limit(20)
        )
        
        result = await self.db.execute(query)
        activities = result.scalars().all()
        
        # Оцениваем влияние каждой активности на аспекты, требующие улучшения
        for activity in activities:
            impact = await self.state_service.calculate_activity_impact_on_state(user_id, activity.id)
            
            # Рассчитываем общую эффективность для улучшения указанных аспектов
            effectiveness = 0
            explanation = []
            
            for aspect, gap in aspects_to_improve.items():
                if aspect == "mood_score":
                    impact_key = "mood_impact"
                elif aspect == "energy_level":
                    impact_key = "energy_impact"
                elif aspect == "stress_level":
                    impact_key = "stress_impact"
                elif aspect == "wellbeing_index":
                    impact_key = "wellbeing_impact"
                else:
                    continue
                
                if impact_key in impact and impact[impact_key] != 0:
                    # Для аспектов, где ниже = лучше (stress), положительное влияние = снижение
                    if aspect in ["stress_level", "anxiety_level"]:
                        if impact[impact_key] < 0:  # Негативное влияние = снижение стресса = хорошо
                            effectiveness += abs(impact[impact_key])
                            explanation.append(f"снижает {aspect.replace('_level', '')} на {abs(impact[impact_key]):.1f}")
                    else:
                        if impact[impact_key] > 0:  # Положительное влияние = улучшение
                            effectiveness += impact[impact_key]
                            explanation.append(f"улучшает {aspect.replace('_score', '').replace('_level', '')} на {impact[impact_key]:.1f}")
            
            if effectiveness > 0:
                activity_impacts[activity.id] = {
                    "activity": activity,
                    "effectiveness": effectiveness,
                    "explanation": ", ".join(explanation)
                }
        
        # Сортируем активности по эффективности
        sorted_activities = sorted(
            activity_impacts.values(),
            key=lambda x: x["effectiveness"],
            reverse=True
        )
        
        # Получаем упражнения для улучшения указанных аспектов
        exercises = []
        if self.exercise_repository:
            categories = []
            if "mood_score" in aspects_to_improve:
                categories.extend(["mood_improvement", "positive_psychology"])
            if "energy_level" in aspects_to_improve:
                categories.extend(["energy_boost", "physical_health"])
            if "stress_level" in aspects_to_improve:
                categories.extend(["stress_reduction", "relaxation"])
            
            if categories:
                exercises = await self.exercise_repository.get_recommended_exercises(
                    categories=categories,
                    limit=3
                )
        
        # Формируем рекомендации
        recommendation_items = []
        
        # Добавляем активности (не более 3)
        for activity_data in sorted_activities[:3]:
            activity = activity_data["activity"]
            recommendation_items.append({
                "item_id": str(activity.id),
                "item_type": "activity",
                "relevance_score": min(activity_data["effectiveness"] / 10, 1.0),
                "explanation": f"Эта активность {activity_data['explanation']}"
            })
        
        # Добавляем упражнения
        for exercise in exercises:
            recommendation_items.append({
                "item_id": str(exercise.id),
                "item_type": "exercise",
                "relevance_score": 0.8,
                "explanation": f"Это упражнение направлено на {exercise.category}"
            })
        
        # Создаем рекомендацию
        if recommendation_items:
            recommendation = RecommendationCreate(
                user_id=str(user_id),
                timestamp=datetime.now(),
                context={
                    "trigger_type": "state_improvement",
                    "priority_level": 3
                },
                recommendation_type="activity",
                recommended_items=recommendation_items
            )
            
            # Сохраняем рекомендацию
            recommendation_id = await self.recommendation_repository.create_recommendation(recommendation)
            
            # Получаем созданную рекомендацию
            recommendation = await self.recommendation_repository.get_recommendation(recommendation_id)
            
            # Кэшируем результат
            await set_cache(cache_key, json.dumps([recommendation.dict()]), expires=1800)  # кэш на 30 минут
            
            return [recommendation]
        
        return []
    
    async def record_recommendation_response(
        self, 
        recommendation_id: str, 
        response_data: RecommendationResponse
    ) -> Recommendation:
        """
        Запись реакции пользователя на рекомендацию (принятие, отклонение, отсрочка).
        
        Параметры:
        - recommendation_id: идентификатор рекомендации
        - response_data: данные о реакции пользователя
        """
        # Получаем рекомендацию
        recommendation = await self.recommendation_repository.get_recommendation(recommendation_id)
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation with ID {recommendation_id} not found"
            )
        
        # Используем метод репозитория для записи реакции
        updated_recommendation = await self.recommendation_repository.record_user_response(
            recommendation_id,
            response_data
        )
        
        # Если пользователь принял рекомендацию и выбрал активность или упражнение
        if response_data.status == "accepted" and response_data.selected_item_id:
            # Определяем тип выбранного элемента
            selected_item_type = None
            for item in recommendation.recommended_items:
                if item["item_id"] == response_data.selected_item_id:
                    selected_item_type = item["item_type"]
                    break
            
            # Если выбрана активность, обновляем ее (помечаем как запланированную)
            if selected_item_type == "activity":
                try:
                    # Получаем активность
                    activity = await self.activity_service.get_activity_by_id(
                        UUID(response_data.selected_item_id),
                        UUID(recommendation.user_id)
                    )
                    
                    # Обновляем активность (помечаем как запланированную)
                    if not activity.is_completed:
                        await self.activity_service.update_activity(
                            UUID(response_data.selected_item_id),
                            {
                                "is_scheduled": True,
                                "scheduled_via_recommendation": True,
                                "recommendation_id": recommendation_id
                            },
                            UUID(recommendation.user_id)
                        )
                except Exception:
                    # Игнорируем ошибки при обновлении активности
                    pass
        
        return updated_recommendation
    
    async def evaluate_recommendation_effectiveness(
        self, 
        recommendation_id: str, 
        effectiveness_data: EffectivenessData
    ) -> Recommendation:
        """
        Оценка эффективности рекомендации после ее выполнения.
        
        Параметры:
        - recommendation_id: идентификатор рекомендации
        - effectiveness_data: данные об эффективности
        """
        # Получаем рекомендацию
        recommendation = await self.recommendation_repository.get_recommendation(recommendation_id)
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation with ID {recommendation_id} not found"
            )
        
        # Используем метод репозитория для записи эффективности
        updated_recommendation = await self.recommendation_repository.record_effectiveness(
            recommendation_id,
            effectiveness_data
        )
        
        # Обновляем модель рекомендаций для пользователя
        await self.update_recommendation_model(UUID(recommendation.user_id))
        
        return updated_recommendation
    
    async def get_activity_recommendations_history(
        self, 
        user_id: UUID, 
        activity_id: UUID
    ) -> List[Recommendation]:
        """
        Получение истории рекомендаций конкретной активности.
        
        Параметры:
        - activity_id: идентификатор активности
        """
        # Получаем все рекомендации пользователя
        recommendations = await self.recommendation_repository.get_user_recommendations(str(user_id))
        
        # Фильтруем рекомендации, содержащие указанную активность
        activity_recommendations = []
        for recommendation in recommendations:
            for item in recommendation.recommended_items:
                if item["item_id"] == str(activity_id) and item["item_type"] == "activity":
                    activity_recommendations.append(recommendation)
                    break
        
        # Сортируем по времени (сначала новые)
        activity_recommendations.sort(key=lambda x: x.timestamp, reverse=True)
        
        return activity_recommendations
    
    async def get_most_effective_recommendations(
        self, 
        user_id: UUID, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Получение наиболее эффективных рекомендаций для пользователя.
        
        Параметры:
        - limit: количество возвращаемых рекомендаций
        """
        # Получаем все рекомендации пользователя с оценкой эффективности
        recommendations = await self.recommendation_repository.get_user_recommendations(str(user_id))
        
        # Фильтруем рекомендации с оценкой эффективности
        effective_recommendations = []
        for recommendation in recommendations:
            if hasattr(recommendation, 'effectiveness') and recommendation.effectiveness:
                if 'user_rating' in recommendation.effectiveness and recommendation.effectiveness['user_rating'] is not None:
                    effective_recommendations.append(recommendation)
        
        # Если нет рекомендаций с оценкой эффективности
        if not effective_recommendations:
            return []
        
        # Сортируем по оценке пользователя (в порядке убывания)
        effective_recommendations.sort(
            key=lambda x: x.effectiveness['user_rating'],
            reverse=True
        )
        
        # Формируем результат
        result = []
        for recommendation in effective_recommendations[:limit]:
            # Получаем выбранный элемент
            selected_item_id = None
            selected_item_type = None
            selected_item_name = None
            
            if hasattr(recommendation, 'user_response') and recommendation.user_response:
                if 'selected_item_id' in recommendation.user_response:
                    selected_item_id = recommendation.user_response['selected_item_id']
                    
                    # Ищем тип элемента
                    for item in recommendation.recommended_items:
                        if item["item_id"] == selected_item_id:
                            selected_item_type = item["item_type"]
                            break
            
            # Получаем название выбранного элемента
            if selected_item_id and selected_item_type:
                if selected_item_type == "activity":
                    try:
                        activity = await self.activity_service.get_activity_by_id(
                            UUID(selected_item_id),
                            UUID(recommendation.user_id)
                        )
                        selected_item_name = activity.title
                    except Exception:
                        selected_item_name = "Неизвестная активность"
                elif selected_item_type == "exercise":
                    try:
                        if self.exercise_repository:
                            exercise = await self.exercise_repository.get_by_id(UUID(selected_item_id))
                            selected_item_name = exercise.title
                        else:
                            selected_item_name = "Неизвестное упражнение"
                    except Exception:
                        selected_item_name = "Неизвестное упражнение"
            
            # Формируем запись
            result.append({
                "recommendation_id": recommendation.id,
                "recommendation_type": recommendation.recommendation_type,
                "timestamp": recommendation.timestamp.isoformat(),
                "user_rating": recommendation.effectiveness['user_rating'],
                "selected_item_type": selected_item_type,
                "selected_item_name": selected_item_name,
                "state_improvement": recommendation.effectiveness.get('state_improvement'),
                "completion_status": recommendation.effectiveness.get('completion_status')
            })
        
        return result
    
    async def update_recommendation_model(self, user_id: UUID) -> bool:
        """
        Обновление модели рекомендаций на основе новых данных.
        В данной реализации производится анализ накопленных данных и оптимизация
        параметров для будущих рекомендаций.
        
        Параметры:
        - user_id: идентификатор пользователя
        """
        # Получаем все рекомендации пользователя с оценкой эффективности
        recommendations = await self.recommendation_repository.get_user_recommendations(str(user_id))
        
        # Фильтруем рекомендации с оценкой эффективности
        effective_recommendations = []
        for recommendation in recommendations:
            if hasattr(recommendation, 'effectiveness') and recommendation.effectiveness:
                if 'user_rating' in recommendation.effectiveness and recommendation.effectiveness['user_rating'] is not None:
                    effective_recommendations.append(recommendation)
        
        # Если недостаточно данных для обновления модели
        if len(effective_recommendations) < 5:
            return False
        
        # Собираем данные о рекомендованных элементах
        item_scores = {}
        
        for recommendation in effective_recommendations:
            # Получаем выбранный элемент
            selected_item_id = None
            if hasattr(recommendation, 'user_response') and recommendation.user_response:
                if 'selected_item_id' in recommendation.user_response:
                    selected_item_id = recommendation.user_response['selected_item_id']
            
            # Если элемент был выбран, обновляем его оценку
            if selected_item_id:
                user_rating = recommendation.effectiveness.get('user_rating', 0)
                state_improvement = recommendation.effectiveness.get('state_improvement', 0)
                
                # Рассчитываем общую оценку (комбинация пользовательской оценки и улучшения состояния)
                if state_improvement is not None:
                    overall_score = user_rating * 0.7 + (state_improvement + 1) * 5 * 0.3
                else:
                    overall_score = user_rating
                
                # Обновляем оценку элемента
                if selected_item_id not in item_scores:
                    item_scores[selected_item_id] = {
                        "scores": [overall_score],
                        "count": 1
                    }
                else:
                    item_scores[selected_item_id]["scores"].append(overall_score)
                    item_scores[selected_item_id]["count"] += 1
        
        # Рассчитываем средние оценки для каждого элемента
        item_average_scores = {}
        for item_id, data in item_scores.items():
            if data["count"] > 0:
                item_average_scores[item_id] = sum(data["scores"]) / data["count"]
        
        # Сохраняем результаты в Redis для использования при генерации будущих рекомендаций
        await set_cache(
            f"recommendation_model:{user_id}",
            json.dumps(item_average_scores),
            expires=86400 * 7  # кэш на 7 дней
        )
        
        return True