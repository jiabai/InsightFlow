class StorageError(Exception):
    """Custom exception for storage-related errors."""
    pass

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class StatusStoreError(Exception):
    """Custom exception for file status store errors."""
    pass

class RedisError(StatusStoreError):
    """Backward-compatible status store exception alias."""
    pass
