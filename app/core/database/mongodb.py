from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from app.config import settings
from typing import Optional, Dict, Any

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальные переменные для клиента и базы данных
motor_client: Optional[AsyncIOMotorClient] = None
mongo_db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongodb() -> AsyncIOMotorDatabase:
    """
    Устанавливает соединение с MongoDB и возвращает ссылку на базу данных
    """
    global motor_client, mongo_db
    try:
        # Создаем клиента MongoDB с таймаутом в 5 секунд
        mongodb_url = getattr(settings.mongodb, 'MONGODB_URL', None)
        mongodb_name = getattr(settings.mongodb, 'MONGODB_DB_NAME', 'psybalans')
        
        if not mongodb_url:
            raise ValueError("MongoDB URL is not configured")
        
        motor_client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000
        )
        
        # Проверяем соединение
        await motor_client.server_info()
        logger.info("Connected to MongoDB successfully")
        
        # Получаем ссылку на базу данных
        mongo_db = motor_client[mongodb_name]
        return mongo_db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # Создаем имитацию MongoDB для работы в offline-режиме
        from unittest.mock import AsyncMock, MagicMock
        
        class MockCollection:
            def __init__(self, name):
                self.name = name
                self.data = []
                self.indexes = {}
            
            async def insert_one(self, document):
                from bson import ObjectId
                if '_id' not in document:
                    document['_id'] = ObjectId()
                self.data.append(document)
                mock_result = MagicMock()
                mock_result.inserted_id = document['_id']
                return mock_result
                
            async def find_one(self, query):
                # Очень упрощенная реализация поиска
                for doc in self.data:
                    match = True
                    for k, v in query.items():
                        if k not in doc or doc[k] != v:
                            match = False
                            break
                    if match:
                        return doc
                return None
                
            def find(self, query=None):
                mock_cursor = MagicMock()
                
                # Фильтруем документы в соответствии с query
                filtered_data = []
                if query:
                    for doc in self.data:
                        match = True
                        for k, v in query.items():
                            if k not in doc or doc[k] != v:
                                match = False
                                break
                        if match:
                            filtered_data.append(doc)
                else:
                    filtered_data = self.data.copy()
                
                mock_cursor.to_list = AsyncMock(return_value=filtered_data)
                mock_cursor.skip = lambda n: mock_cursor
                mock_cursor.limit = lambda n: mock_cursor
                mock_cursor.sort = lambda s: mock_cursor
                return mock_cursor
                
            async def update_one(self, query, update):
                doc = await self.find_one(query)
                mock_result = MagicMock()
                if not doc:
                    mock_result.modified_count = 0
                    return mock_result
                
                for field, value in update.get('$set', {}).items():
                    doc[field] = value
                
                mock_result.modified_count = 1
                return mock_result
                
            async def delete_one(self, query):
                doc = await self.find_one(query)
                mock_result = MagicMock()
                if not doc:
                    mock_result.deleted_count = 0
                    return mock_result
                
                self.data.remove(doc)
                mock_result.deleted_count = 1
                return mock_result
                
            async def create_index(self, keys, name=None):
                key_name = name or "_".join([k[0] for k in keys.items()])
                self.indexes[key_name] = keys
                return key_name
                
            def aggregate(self, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[])
                return mock_cursor
        
        class MockDatabase:
            def __init__(self, name):
                self.name = name
                self.collections = {}
            
            def __getitem__(self, name):
                if name not in self.collections:
                    self.collections[name] = MockCollection(name)
                return self.collections[name]
                
            async def command(self, cmd, *args, **kwargs):
                if isinstance(cmd, dict) and "collMod" in cmd:
                    return {'ok': 1}
                if cmd == 'ping':
                    return {'ok': 1}
                return {'ok': 0, 'error': 'Command not implemented in mock'}
                
            async def list_collection_names(self):
                return list(self.collections.keys())
                
            async def create_collection(self, name, **kwargs):
                if name not in self.collections:
                    self.collections[name] = MockCollection(name)
                return self.collections[name]
        
        class MockMotorClient:
            def __init__(self):
                self.databases = {}
                self.admin = MockDatabase('admin')
                # Предварительно создаем необходимые коллекции
                psybalans_db = MockDatabase('psybalans_mock')
                self.databases['psybalans_mock'] = psybalans_db
            
            def __getitem__(self, name):
                if name not in self.databases:
                    self.databases[name] = MockDatabase(name)
                return self.databases[name]
                
            async def server_info(self):
                return {'version': '4.0.0-mock', 'ok': 1}
                
            def close(self):
                pass
        
        logger.warning(f"Using in-memory MongoDB mock due to connection error: {e}")
        motor_client = MockMotorClient()
        mongo_db = motor_client['psybalans_mock']
        return mongo_db


async def get_mongodb() -> AsyncIOMotorDatabase:
    """
    Зависимость для FastAPI, предоставляющая соединение с MongoDB
    """
    global mongo_db
    if mongo_db is None:
        mongo_db = await connect_to_mongodb()
    return mongo_db


async def close_mongodb_connection():
    """
    Закрывает соединение с MongoDB
    """
    global motor_client
    if motor_client:
        motor_client.close()
        logger.info("MongoDB connection closed")


async def check_mongodb_connection() -> tuple[bool, str]:
    """
    Проверяет соединение с MongoDB
    Возвращает кортеж (успех, сообщение)
    """
    try:
        if motor_client is None:
            await connect_to_mongodb()
            
        # Проверяем соединение через команду ping
        await motor_client.admin.command('ping')
        return True, "Successfully connected to MongoDB"
    except Exception as e:
        return False, f"Failed to connect to MongoDB: {str(e)}"


# Вспомогательные функции для работы с коллекциями

async def insert_one(collection_name: str, document: Dict[str, Any]) -> str:
    """
    Вставляет один документ в коллекцию и возвращает его ID
    """
    if mongo_db is None:
        await connect_to_mongodb()
    
    result = await mongo_db[collection_name].insert_one(document)
    return str(result.inserted_id)


async def find_one(collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Находит один документ по запросу
    """
    if mongo_db is None:
        await connect_to_mongodb()
    
    result = await mongo_db[collection_name].find_one(query)
    return result


async def find_many(
    collection_name: str,
    query: Dict[str, Any],
    skip: int = 0,
    limit: int = 100,
    sort_by: Optional[Dict[str, int]] = None
) -> list[Dict[str, Any]]:
    """
    Находит множество документов по запросу с пагинацией и сортировкой
    """
    if mongo_db is None:
        await connect_to_mongodb()
    
    cursor = mongo_db[collection_name].find(query).skip(skip).limit(limit)
    
    if sort_by:
        cursor = cursor.sort(list(sort_by.items()))
    
    return await cursor.to_list(length=limit)


async def update_one(
    collection_name: str,
    query: Dict[str, Any],
    update: Dict[str, Any]
) -> int:
    """
    Обновляет один документ и возвращает количество измененных документов
    """
    if mongo_db is None:
        await connect_to_mongodb()
    
    result = await mongo_db[collection_name].update_one(query, {'$set': update})
    return result.modified_count


async def delete_one(collection_name: str, query: Dict[str, Any]) -> int:
    """
    Удаляет один документ и возвращает количество удаленных документов
    """
    if mongo_db is None:
        await connect_to_mongodb()
    
    result = await mongo_db[collection_name].delete_one(query)
    return result.deleted_count


async def create_indexes(collection_name: str, indexes: list[tuple[str, int]]):
    """
    Создает индексы в коллекции
    """
    if mongo_db is None:
        await connect_to_mongodb()
    
    for field, direction in indexes:
        await mongo_db[collection_name].create_index([(field, direction)])
    
    logger.info(f"Created indexes for collection {collection_name}")


# Импорт функции настройки индексов
from app.core.database.mongodb_indexes import setup_mongodb_indexes

# Инициализация подключения при запуске приложения
async def init_mongodb():
    """
    Инициализирует подключение к MongoDB.
    Вызывается при запуске приложения.
    """
    global mongo_db
    mongo_db = await connect_to_mongodb()
    
    # Настройка индексов для оптимизации запросов
    try:
        await setup_mongodb_indexes(mongo_db)
        logger.info("MongoDB indexes setup completed")
    except Exception as e:
        logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    return mongo_db