import asyncio

from server.common.file_status_store import LocalFileStatusStore


async def read_file_status(key: str):
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
    test_key = "fa43b6889c67ccb96dfcc6d06ad01602b4631a87521d3fd5fbc0bc4195d84372"
    asyncio.run(read_file_status(test_key))
