import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.infrastructure.redis.factory import REDIS_CONN

# =============================================================================
# Redis工厂功能验证
# =============================================================================

async def validate_redis_factory():
    """Redis工厂功能验证"""
    print("=" * 60)
    print("🔍 Redis工厂功能验证开始")
    print("=" * 60)
    
    validation_results = {
        "health_check": False,
        "basic_operations": False,
        "hash_operations": False,
        "list_operations": False,
        "set_operations": False,
        "sorted_set_operations": False,
        "expire_operations": False,
        "transaction_operations": False,
        "queue_operations": False,
        "distributed_lock": False,
        "batch_operations": False
    }
    
    try:
        # 1. 健康检查验证
        print("\n📋 1. 健康检查验证")
        health_ok = await REDIS_CONN.health_check()
        validation_results["health_check"] = health_ok
        print(f"   健康检查: {'✅ 通过' if health_ok else '❌ 失败'}")
        
        if not health_ok:
            print("   ⚠️  Redis连接失败，跳过其他验证")
            return validation_results
        
        # 2. 基础操作验证
        print("\n📋 2. 基础操作验证")
        test_key = "test:basic:key"
        test_value = "test_value"
        test_obj = {"name": "test", "value": 123}
        
        # SET操作
        set_result = await REDIS_CONN.set(test_key, test_value, exp=60)
        print(f"   SET操作: {'✅ 通过' if set_result else '❌ 失败'}")
        
        # GET操作
        get_result = await REDIS_CONN.get(test_key)
        get_ok = get_result == test_value
        print(f"   GET操作: {'✅ 通过' if get_ok else '❌ 失败'}")
        
        # SET_OBJ操作
        set_obj_result = await REDIS_CONN.set_obj(f"{test_key}:obj", test_obj, exp=60)
        print(f"   SET_OBJ操作: {'✅ 通过' if set_obj_result else '❌ 失败'}")
        
        # EXISTS操作
        exist_result = await REDIS_CONN.exist(test_key)
        print(f"   EXISTS操作: {'✅ 通过' if exist_result else '❌ 失败'}")
        
        # DELETE操作
        delete_result = await REDIS_CONN.delete(test_key)
        print(f"   DELETE操作: {'✅ 通过' if delete_result else '❌ 失败'}")
        
        validation_results["basic_operations"] = all([set_result, get_ok, set_obj_result, exist_result, delete_result])
        
        # 3. 哈希操作验证
        print("\n📋 3. 哈希操作验证")
        hash_name = "test:hash"
        hash_key = "field1"
        hash_value = "value1"
        
        # HSET操作
        hset_result = await REDIS_CONN.hset(hash_name, hash_key, hash_value)
        print(f"   HSET操作: {'✅ 通过' if hset_result else '❌ 失败'}")
        
        # HGET操作
        hget_result = await REDIS_CONN.hget(hash_name, hash_key)
        hget_ok = hget_result == hash_value
        print(f"   HGET操作: {'✅ 通过' if hget_ok else '❌ 失败'}")
        
        # HGETALL操作
        hgetall_result = await REDIS_CONN.hgetall(hash_name)
        hgetall_ok = hash_key in hgetall_result and hgetall_result[hash_key] == hash_value
        print(f"   HGETALL操作: {'✅ 通过' if hgetall_ok else '❌ 失败'}")
        
        # HDEL操作
        hdel_result = await REDIS_CONN.hdel(hash_name, hash_key)
        print(f"   HDEL操作: {'✅ 通过' if hdel_result > 0 else '❌ 失败'}")
        
        validation_results["hash_operations"] = all([hset_result, hget_ok, hgetall_ok, hdel_result > 0])
        
        # 4. 列表操作验证
        print("\n📋 4. 列表操作验证")
        list_name = "test:list"
        
        # LPUSH操作
        lpush_result = await REDIS_CONN.lpush(list_name, "item1", "item2", "item3")
        print(f"   LPUSH操作: {'✅ 通过' if lpush_result > 0 else '❌ 失败'}")
        
        # LLEN操作
        llen_result = await REDIS_CONN.llen(list_name)
        llen_ok = llen_result == 3
        print(f"   LLEN操作: {'✅ 通过' if llen_ok else '❌ 失败'}")
        
        # RPOP操作
        rpop_result = await REDIS_CONN.rpop(list_name)
        rpop_ok = rpop_result == "item1"  # 后进先出，所以是item1
        print(f"   RPOP操作: {'✅ 通过' if rpop_ok else '❌ 失败'}")
        
        # 清理
        await REDIS_CONN.delete(list_name)
        
        validation_results["list_operations"] = all([lpush_result > 0, llen_ok, rpop_ok])
        
        # 5. 集合操作验证
        print("\n📋 5. 集合操作验证")
        set_key = "test:set"
        
        # SADD操作
        sadd_result = await REDIS_CONN.sadd(set_key, "member1")
        print(f"   SADD操作: {'✅ 通过' if sadd_result else '❌ 失败'}")
        
        # SISMEMBER操作
        sismember_result = await REDIS_CONN.sismember(set_key, "member1")
        print(f"   SISMEMBER操作: {'✅ 通过' if sismember_result else '❌ 失败'}")
        
        # SMEMBERS操作
        smembers_result = await REDIS_CONN.smembers(set_key)
        smembers_ok = "member1" in smembers_result
        print(f"   SMEMBERS操作: {'✅ 通过' if smembers_ok else '❌ 失败'}")
        
        # SREM操作
        srem_result = await REDIS_CONN.srem(set_key, "member1")
        print(f"   SREM操作: {'✅ 通过' if srem_result else '❌ 失败'}")
        
        # 清理
        await REDIS_CONN.delete(set_key)
        
        validation_results["set_operations"] = all([sadd_result, sismember_result, smembers_ok, srem_result])
        
        # 6. 有序集合操作验证
        print("\n📋 6. 有序集合操作验证")
        zset_key = "test:zset"
        
        # ZADD操作
        zadd_result = await REDIS_CONN.zadd(zset_key, "member1", 1.0)
        print(f"   ZADD操作: {'✅ 通过' if zadd_result else '❌ 失败'}")
        
        # ZCOUNT操作
        zcount_result = await REDIS_CONN.zcount(zset_key, 0, 2)
        zcount_ok = zcount_result == 1
        print(f"   ZCOUNT操作: {'✅ 通过' if zcount_ok else '❌ 失败'}")
        
        # ZRANGEBYSCORE操作
        zrangebyscore_result = await REDIS_CONN.zrangebyscore(zset_key, 0, 2)
        zrangebyscore_ok = "member1" in zrangebyscore_result
        print(f"   ZRANGEBYSCORE操作: {'✅ 通过' if zrangebyscore_ok else '❌ 失败'}")
        
        # 清理
        await REDIS_CONN.delete(zset_key)
        
        validation_results["sorted_set_operations"] = all([zadd_result, zcount_ok, zrangebyscore_ok])
        
        # 7. 过期时间操作验证
        print("\n📋 7. 过期时间操作验证")
        expire_key = "test:expire"
        
        # 设置键值
        await REDIS_CONN.set(expire_key, "test", exp=5)
        
        # EXPIRE操作
        expire_result = await REDIS_CONN.expire(expire_key, 10)
        print(f"   EXPIRE操作: {'✅ 通过' if expire_result else '❌ 失败'}")
        
        # TTL操作
        ttl_result = await REDIS_CONN.ttl(expire_key)
        ttl_ok = ttl_result > 0
        print(f"   TTL操作: {'✅ 通过' if ttl_ok else '❌ 失败'}")
        
        # 清理
        await REDIS_CONN.delete(expire_key)
        
        validation_results["expire_operations"] = all([expire_result, ttl_ok])
        
        # 8. 事务操作验证
        print("\n📋 8. 事务操作验证")
        transaction_key = "test:transaction"
        
        # TRANSACTION操作
        transaction_result = await REDIS_CONN.transaction(transaction_key, "transaction_value", expire=60)
        print(f"   TRANSACTION操作: {'✅ 通过' if transaction_result else '❌ 失败'}")
        
        # 验证事务结果
        transaction_get = await REDIS_CONN.get(transaction_key)
        transaction_ok = transaction_get == "transaction_value"
        print(f"   事务结果验证: {'✅ 通过' if transaction_ok else '❌ 失败'}")
        
        # 清理
        await REDIS_CONN.delete(transaction_key)
        
        validation_results["transaction_operations"] = all([transaction_result, transaction_ok])
        
        # 9. 消息队列操作验证
        print("\n📋 9. 消息队列操作验证")
        queue_name = "test:queue"
        group_name = "test_group"
        consumer_name = "test_consumer"
        test_message = {"id": 1, "content": "test message"}
        
        # QUEUE_PRODUCT操作
        queue_product_result = await REDIS_CONN.queue_product(queue_name, test_message)
        print(f"   QUEUE_PRODUCT操作: {'✅ 通过' if queue_product_result else '❌ 失败'}")
        
        # QUEUE_CONSUMER操作
        queue_consumer_result = await REDIS_CONN.queue_consumer(queue_name, group_name, consumer_name)
        queue_consumer_ok = queue_consumer_result is not None
        print(f"   QUEUE_CONSUMER操作: {'✅ 通过' if queue_consumer_ok else '❌ 失败'}")
        
        if queue_consumer_result:
            # 确认消息
            ack_result = await queue_consumer_result.ack()
            print(f"   消息确认: {'✅ 通过' if ack_result else '❌ 失败'}")
        
        validation_results["queue_operations"] = all([queue_product_result, queue_consumer_ok])
        
        # 10. 分布式锁验证
        print("\n📋 10. 分布式锁验证")
        lock_key = "test:lock"
        
        # 获取锁
        lock = REDIS_CONN.get_lock(lock_key, timeout=5)
        acquire_result = await lock.acquire()
        print(f"   锁获取: {'✅ 通过' if acquire_result else '❌ 失败'}")
        
        # 释放锁
        release_result = await lock.release()
        print(f"   锁释放: {'✅ 通过' if release_result else '❌ 失败'}")
        
        validation_results["distributed_lock"] = all([acquire_result, release_result])
        
        # 11. 批量操作验证
        print("\n📋 11. 批量操作验证")
        batch_keys = ["test:batch:1", "test:batch:2", "test:batch:3"]
        batch_values = ["value1", "value2", "value3"]
        batch_mapping = dict(zip(batch_keys, batch_values))
        
        # MSET操作
        mset_result = await REDIS_CONN.mset(batch_mapping)
        print(f"   MSET操作: {'✅ 通过' if mset_result else '❌ 失败'}")
        
        # MGET操作
        mget_result = await REDIS_CONN.mget(batch_keys)
        mget_ok = mget_result == batch_values
        print(f"   MGET操作: {'✅ 通过' if mget_ok else '❌ 失败'}")
        
        # 清理
        for key in batch_keys:
            await REDIS_CONN.delete(key)
        
        validation_results["batch_operations"] = all([mset_result, mget_ok])
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        logging.exception("Redis工厂验证异常")
    
    # 输出验证结果汇总
    print("\n" + "=" * 60)
    print("📊 Redis工厂验证结果汇总")
    print("=" * 60)
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有Redis功能验证通过！")
    else:
        print("⚠️  部分Redis功能验证失败，请检查配置和连接")
    
    print("=" * 60)
    
    return validation_results
if __name__ == "__main__":
    import asyncio
    import sys
    
    # 设置控制台编码为UTF-8
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    async def run_validation():
        """运行Redis工厂验证"""
        try:
            # 设置日志级别
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            print("🚀 启动Redis工厂功能验证...")
            await validate_redis_factory()
            
        except KeyboardInterrupt:
            print("\n⏹️  验证被用户中断")
        except Exception as e:
            print(f"\n💥 验证过程中发生严重错误: {e}")
            logging.exception("Redis工厂验证严重错误")
        finally:
            # 清理资源
            try:
                await REDIS_CONN.close()
                print("🔒 Redis连接已关闭")
            except Exception as e:
                print(f"⚠️  关闭Redis连接时出错: {e}")
    
    # 运行验证
    asyncio.run(run_validation())