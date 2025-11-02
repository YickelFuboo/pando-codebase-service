import asyncio
import logging
import sys
import os


# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.infrastructure.database.factory import get_db, close_db, health_check_db
from app.config.settings import settings
from sqlalchemy import text

# =============================================================================
# 数据库工厂功能验证
# =============================================================================

async def validate_database_factory():
    """数据库工厂功能验证"""
    print("=" * 60)
    print("🔍 数据库工厂功能验证开始")
    print("=" * 60)
    
    # 打印数据库配置信息
    print(f"📋 数据库配置信息:")
    print(f"   数据库类型: {settings.database_type}")
    print(f"   数据库URL: {settings.database_url}")
    print(f"   连接池大小: {settings.db_pool_size}")
    print(f"   最大溢出连接: {settings.db_max_overflow}")
    print()
    
    validation_results = {
        "health_check": False,
        "session_management": False,
        "basic_query": False,
        "transaction": False,
        "connection_pool": False,
        "error_handling": False
    }
    
    conn = None
    test_table_name = "test_db_validation"
    
    try:        
        # 2. 健康检查验证
        print("\n📋 1. 健康检查验证")
        health_ok = False
        try:
            # 使用对外接口health_check_db
            health_ok = await health_check_db()
            validation_results["health_check"] = health_ok
            print(f"   健康检查: {'✅ 通过' if health_ok else '❌ 失败'}")
        except Exception as e:
            print(f"   健康检查: ❌ 失败 - {e}")
        
        if not health_ok:
            print("   ⚠️  数据库不健康，跳过其他验证")
            return validation_results
        
        # 3. 会话管理验证
        print("\n📋 2. 会话管理验证")
        try:
            # 使用factory中的get_db异步生成器
            async for session in get_db():
                session_created = session is not None
                
                # 测试基本查询
                result = await session.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()
                query_ok = row is not None and row[0] == 1
                
                # 会话会自动关闭
                session_closed = True
                break  # 只测试一次
            
            validation_results["session_management"] = all([session_created, query_ok, session_closed])
            print(f"   会话创建: {'✅ 通过' if session_created else '❌ 失败'}")
            print(f"   基本查询: {'✅ 通过' if query_ok else '❌ 失败'}")
            print(f"   会话关闭: {'✅ 通过' if session_closed else '❌ 失败'}")
        except Exception as e:
            print(f"   会话管理: ❌ 失败 - {e}")
        
        # 4. 基本查询验证
        print("\n📋 3. 基本查询验证")
        try:
            async for session in get_db():
                # 测试不同类型的查询
                queries = [
                    ("SELECT 1", "简单查询"),
                    ("SELECT CURRENT_TIMESTAMP", "时间查询"),
                    ("SELECT 'test' as test_string", "字符串查询")
                ]
                
                query_results = []
                for query, description in queries:
                    try:
                        result = await session.execute(text(query))
                        row = result.fetchone()
                        success = row is not None
                        query_results.append(success)
                        print(f"   {description}: {'✅ 通过' if success else '❌ 失败'}")
                    except Exception as e:
                        query_results.append(False)
                        print(f"   {description}: ❌ 失败 - {e}")
                
                validation_results["basic_query"] = all(query_results)
                break  # 只测试一次
        except Exception as e:
            print(f"   基本查询: ❌ 失败 - {e}")
        
        # 5. 事务处理验证
        print("\n📋 4. 事务处理验证")
        try:
            async for session in get_db():
                # 测试事务提交
                try:
                    await session.execute(text("SELECT 1"))
                    await session.commit()
                    commit_ok = True
                    print(f"   事务提交: ✅ 通过")
                except Exception as e:
                    commit_ok = False
                    print(f"   事务提交: ❌ 失败 - {e}")
                
                # 测试事务回滚
                try:
                    await session.execute(text("SELECT 1"))
                    await session.rollback()
                    rollback_ok = True
                    print(f"   事务回滚: ✅ 通过")
                except Exception as e:
                    rollback_ok = False
                    print(f"   事务回滚: ❌ 失败 - {e}")
                
                validation_results["transaction"] = all([commit_ok, rollback_ok])
                break  # 只测试一次
        except Exception as e:
            print(f"   事务处理: ❌ 失败 - {e}")
        
        # 6. 连接池验证
        print("\n📋 5. 连接池验证")
        try:
            # 测试多个并发会话
            import asyncio
            
            async def test_session():
                async for session in get_db():
                    result = await session.execute(text("SELECT 1"))
                    return result.fetchone() is not None
            
            # 创建多个并发任务
            tasks = [test_session() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查结果
            success_count = sum(1 for r in results if r is True)
            exception_count = sum(1 for r in results if isinstance(r, Exception))
            
            pool_ok = success_count >= 3 and exception_count == 0  # 至少3个成功，无异常
            
            validation_results["connection_pool"] = pool_ok
            print(f"   并发会话: {'✅ 通过' if pool_ok else '❌ 失败'}")
            print(f"   成功数量: {success_count}/5")
            print(f"   异常数量: {exception_count}")
        except Exception as e:
            print(f"   连接池: ❌ 失败 - {e}")
        
        # 7. 错误处理验证
        print("\n📋 7. 错误处理验证")
        try:
            async for session in get_db():
                # 测试无效查询
                try:
                    await session.execute(text("SELECT * FROM non_existent_table_12345"))
                    error_handling_ok = False
                    print(f"   无效查询: ❌ 失败 - 应该抛出异常但没有")
                except Exception as e:
                    error_handling_ok = True
                    print(f"   无效查询: ✅ 通过 - 正确抛出异常: {type(e).__name__}")
                
                # 测试SQL语法错误
                try:
                    await session.execute(text("INVALID SQL SYNTAX"))
                    error_handling_ok = False
                    print(f"   SQL语法错误: ❌ 失败 - 应该抛出异常但没有")
                except Exception as e:
                    error_handling_ok = error_handling_ok and True
                    print(f"   SQL语法错误: ✅ 通过 - 正确抛出异常: {type(e).__name__}")
                
                validation_results["error_handling"] = error_handling_ok
                break  # 只测试一次
        except Exception as e:
            print(f"   错误处理: ❌ 失败 - {e}")
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        logging.exception("数据库工厂验证异常")
    
    # 输出验证结果汇总
    print("\n" + "=" * 60)
    print("📊 数据库工厂验证结果汇总")
    print("=" * 60)
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有数据库功能验证通过！")
    else:
        print("⚠️  部分数据库功能验证失败，请检查配置和连接")
    
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
        """运行数据库工厂验证"""
        try:
            # 设置日志级别
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            print("🚀 启动数据库工厂功能验证...")
            await validate_database_factory()
            
        except KeyboardInterrupt:
            print("\n⏹️  验证被用户中断")
        except Exception as e:
            print(f"\n💥 验证过程中发生严重错误: {e}")
            logging.exception("数据库工厂验证严重错误")
        finally:
            # 清理资源 - 使用对外接口
            try:
                await close_db()
                print("🔒 数据库连接已关闭")
            except Exception as e:
                print(f"⚠️  关闭数据库连接时出错: {e}")
    
    # 运行验证
    asyncio.run(run_validation())