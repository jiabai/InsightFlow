class StorageError(Exception):
    """Custom exception for storage-related errors."""
    pass

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class RedisError(Exception):
    """Custom exception for Redis-related errors."""
    pass