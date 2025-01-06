import redis
from collections import defaultdict

# Временное хранилище в памяти
class MemoryStorage:
    def __init__(self):
        self.data = defaultdict(dict)
        self.sessions = {}
    
    def hset(self, key, mapping):
        self.data[key].update(mapping)
    
    def hget(self, key, field):
        return self.data[key].get(field)
    
    def hgetall(self, key):
        return self.data[key]
    
    def set(self, key, value, ex=None):
        self.sessions[key] = value
    
    def get(self, key):
        return self.sessions.get(key)
    
    def delete(self, key):
        if key in self.sessions:
            del self.sessions[key]
        if key in self.data:
            del self.data[key]

# Инициализация хранилища
def init_storage():
    try:
        r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("Redis подключен успешно")
        return r
    except:
        print("Redis недоступен, используем хранение в памяти")
        return MemoryStorage()

# Глобальный экземпляр хранилища
storage = init_storage() 