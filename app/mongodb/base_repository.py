"""
Базовый репозиторий для работы с MongoDB.
Предоставляет абстракцию для выполнения общих операций с коллекциями MongoDB.
"""
import logging
from typing import Dict, Any, List, Optional, Type, Generic, TypeVar
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.mongodb import get_mongodb

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Типовой параметр для generic класса

class MongoDBBaseRepository(Generic[T]):
    """
    Базовый класс репозитория для работы с MongoDB.
    Предоставляет основные методы для CRUD операций с коллекцией.
    """
    
    def __init__(self, collection_name: str):
        """
        Инициализирует репозиторий с указанным именем коллекции.
        
        Args:
            collection_name: Название коллекции в MongoDB
        """
        self.collection_name = collection_name
    
    async def _get_db(self) -> AsyncIOMotorDatabase:
        """
        Получает объект базы данных MongoDB.
        
        Returns:
            AsyncIOMotorDatabase: Объект базы данных MongoDB
        """
        return await get_mongodb()
        
    async def create(self, data: Dict[str, Any]) -> str:
        """
        Создает новый документ в коллекции.
        
        Args:
            data: Данные для создания документа
            
        Returns:
            str: ID созданного документа
        """
        try:
            db = await self._get_db()
            
            # Добавляем временные метки
            now = datetime.utcnow()
            if 'created_at' not in data:
                data['created_at'] = now
            data['updated_at'] = now
            
            result = await db[self.collection_name].insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating document in {self.collection_name}: {e}")
            raise
    
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Получает документ по его ID.
        
        Args:
            id: ID документа
            
        Returns:
            Optional[Dict[str, Any]]: Документ или None, если документ не найден
        """
        try:
            db = await self._get_db()
            result = await db[self.collection_name].find_one({"_id": ObjectId(id)})
            if result:
                result["_id"] = str(result["_id"])  # Преобразуем ObjectId в строку для JSON-сериализации
            return result
        except Exception as e:
            logger.error(f"Error getting document {id} from {self.collection_name}: {e}")
            raise
    
    async def get_many(
        self,
        query: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "timestamp",
        sort_order: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Получает множество документов по запросу с пагинацией и сортировкой.
        
        Args:
            query: Запрос для поиска документов
            skip: Количество документов для пропуска (для пагинации)
            limit: Максимальное количество документов для возврата
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (1 для возрастания, -1 для убывания)
            
        Returns:
            List[Dict[str, Any]]: Список найденных документов
        """
        try:
            db = await self._get_db()
            cursor = db[self.collection_name].find(query)
            cursor = cursor.sort(sort_by, sort_order).skip(skip).limit(limit)
            
            results = await cursor.to_list(length=limit)
            
            # Преобразуем ObjectId в строки для JSON-сериализации
            for result in results:
                result["_id"] = str(result["_id"])
                
            return results
        except Exception as e:
            logger.error(f"Error getting documents from {self.collection_name}: {e}")
            raise
    
    async def update(self, id: str, data: Dict[str, Any]) -> bool:
        """
        Обновляет документ по его ID.
        
        Args:
            id: ID документа
            data: Данные для обновления
            
        Returns:
            bool: True, если документ был обновлен, иначе False
        """
        try:
            db = await self._get_db()
            
            # Добавляем метку времени обновления
            update_data = data.copy()
            update_data["updated_at"] = datetime.utcnow()
            
            result = await db[self.collection_name].update_one(
                {"_id": ObjectId(id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating document {id} in {self.collection_name}: {e}")
            raise
    
    async def delete(self, id: str) -> bool:
        """
        Удаляет документ по его ID.
        
        Args:
            id: ID документа
            
        Returns:
            bool: True, если документ был удален, иначе False
        """
        try:
            db = await self._get_db()
            result = await db[self.collection_name].delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document {id} from {self.collection_name}: {e}")
            raise
    
    async def exists(self, query: Dict[str, Any]) -> bool:
        """
        Проверяет существование документа по запросу.
        
        Args:
            query: Запрос для поиска документа
            
        Returns:
            bool: True, если документ существует, иначе False
        """
        try:
            db = await self._get_db()
            count = await db[self.collection_name].count_documents(query)
            return count > 0
        except Exception as e:
            logger.error(f"Error checking existence in {self.collection_name}: {e}")
            raise
    
    async def count(self, query: Dict[str, Any]) -> int:
        """
        Подсчитывает количество документов, соответствующих запросу.
        
        Args:
            query: Запрос для поиска документов
            
        Returns:
            int: Количество документов
        """
        try:
            db = await self._get_db()
            return await db[self.collection_name].count_documents(query)
        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {e}")
            raise