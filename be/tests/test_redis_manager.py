import pytest
from unittest.mock import AsyncMock, patch
import aioredis
from be.common.redis_manager import RedisManager
from be.common.exceptions import RedisError

@pytest.fixture
def mock_redis_client():
    """Fixture for a mocked aioredis client."""
    mock = AsyncMock()
    mock.ping.return_value = True
    return mock

@pytest.fixture
def manager_factory(mock_redis_client):
    """Factory fixture to create an initialized RedisManager instance."""
    async def _factory():
        with patch('aioredis.create_redis_pool', return_value=mock_redis_client):
            instance = RedisManager()
            await instance.initialize()
            return instance
    return _factory

@pytest.mark.asyncio
async def test_init_redis_success(manager_factory, mock_redis_client):
    """Test successful Redis initialization."""
    manager = await manager_factory()
    mock_redis_client.ping.assert_called_once()
    assert manager.redis_client is not None

@pytest.mark.asyncio
async def test_init_redis_failure():
    """Test Redis initialization failure due to connection error."""
    mock_redis_client = AsyncMock()
    mock_redis_client.ping.side_effect = aioredis.ConnectionClosedError("Connection failed")
    with patch('aioredis.create_redis_pool', return_value=mock_redis_client):
        manager = RedisManager()
        with pytest.raises(RedisError, match="Failed to connect to Redis"):
            await manager.initialize()

@pytest.mark.asyncio
async def test_set_file_status_success(manager_factory, mock_redis_client):
    """Test setting file status successfully."""
    manager = await manager_factory()
    file_id = "test_file_id"
    status = "Processing"
    await manager.set_file_status(file_id, status)
    mock_redis_client.set.assert_called_once_with(file_id, status)

@pytest.mark.asyncio
async def test_set_file_status_failure(manager_factory, mock_redis_client):
    """Test setting file status failure due to Redis error."""
    manager = await manager_factory()
    mock_redis_client.set.side_effect = aioredis.RedisError("Redis write error")
    file_id = "test_file_id"
    status = "Processing"
    with pytest.raises(RedisError, match="Failed to set file status"):
        await manager.set_file_status(file_id, status)

@pytest.mark.asyncio
async def test_get_file_status_success(manager_factory, mock_redis_client):
    """Test getting file status successfully."""
    manager = await manager_factory()
    file_id = "test_file_id"
    expected_status = "Completed"
    mock_redis_client.get.return_value = expected_status
    status = await manager.get_file_status(file_id)
    mock_redis_client.get.assert_called_once_with(file_id)
    assert status == expected_status

@pytest.mark.asyncio
async def test_get_file_status_not_found(manager_factory, mock_redis_client):
    """Test getting file status when key does not exist."""
    manager = await manager_factory()
    file_id = "non_existent_file_id"
    mock_redis_client.get.return_value = None
    status = await manager.get_file_status(file_id)
    mock_redis_client.get.assert_called_once_with(file_id)
    assert status is None

@pytest.mark.asyncio
async def test_get_file_status_failure(manager_factory, mock_redis_client):
    """Test getting file status failure due to Redis error."""
    manager = await manager_factory()
    mock_redis_client.get.side_effect = aioredis.RedisError("Redis read error")
    file_id = "test_file_id"
    with pytest.raises(RedisError, match="Failed to get file status"):
        await manager.get_file_status(file_id)

@pytest.mark.asyncio
async def test_delete_file_status_success(manager_factory, mock_redis_client):
    """Test deleting file status successfully."""
    manager = await manager_factory()
    file_id = "test_file_id"
    await manager.delete_file_status(file_id)
    mock_redis_client.delete.assert_called_once_with(file_id)

@pytest.mark.asyncio
async def test_delete_file_status_failure(manager_factory, mock_redis_client):
    """Test deleting file status failure due to Redis error."""
    manager = await manager_factory()
    mock_redis_client.delete.side_effect = aioredis.RedisError("Redis delete error")
    file_id = "test_file_id"
    with pytest.raises(RedisError, match="Failed to delete file status"):
        await manager.delete_file_status(file_id)