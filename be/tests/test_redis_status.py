import redis

# Redis配置
REDIS_HOST = "192.168.31.233"
REDIS_PORT = 6379

# 创建Redis连接
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def test_read_redis_key(key: str):
    """
    测试读取 Redis 中指定 key 的值。
    """
    try:
        value = redis_client.get(key)
        if value is not None:
            print(f"成功读取 Redis Key '{key}': {value}")
            return value
        else:
            print(f"Redis Key '{key}' 不存在或值为 None")
            return None
    except redis.RedisError as e:
        print(f"读取 Redis Key '{key}' 失败: {e}")
        return None

if __name__ == "__main__":
    # 替换为你要测试的实际 key
    TEST_KEY = "a0b111ca3407ff23e269215869205257c1a0235d8376ff4678784bf367d8ae0b"
    test_read_redis_key(TEST_KEY)
