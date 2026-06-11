import asyncio

from server.common.file_status_store import LocalFileStatusStore


async def test_read_file_status(key: str):
    """Read a status value from the local file status store."""
    store = LocalFileStatusStore()
    await store.initialize()
    value = await store.get_file_status(key)
    if value is not None:
        print(f"Successfully read status '{key}': {value}")
        return value

    print(f"Status '{key}' does not exist")
    return None


if __name__ == "__main__":
    test_key = "3a8e2d0f03fcb4162c0d612f8e6e8f9b646ca2d61a30c8c10c7d51999085fc9f"
    asyncio.run(test_read_file_status(test_key))
