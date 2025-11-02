

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.infrastructure.vector_store.factory import VECTOR_STORE_CONN

# =============================================================================
# 向量存储工厂功能验证
# =============================================================================

async def validate_vector_store_factory():
    """向量存储工厂功能验证"""
    print("=" * 60)
    print("🔍 向量存储工厂功能验证开始")
    print("=" * 60)
    
    validation_results = {
        "connection": False,
        "health_check": False,
        "space_management": False,
        "document_crud": False,
        "search_operations": False,
        "sql_operations": False
    }
    
    conn = None
    test_space_name = "test_vector_space"
    
    try:
        # 1. 连接创建验证
        print("\n📋 1. 连接创建验证")
        try:
            # 使用全局连接初始化函数
            global VECTOR_STORE_CONN
            conn = VECTOR_STORE_CONN
            
            if conn is None:
                print(f"   连接创建: ❌ 失败 - 全局连接未初始化")
                return validation_results
            
            validation_results["connection"] = True
            print(f"   连接创建: ✅ 通过")
            print(f"   数据库类型: {conn.get_db_type()}")
        except Exception as e:
            print(f"   连接创建: ❌ 失败 - {e}")
            return validation_results
        
        # 2. 健康检查验证
        print("\n📋 2. 健康检查验证")
        try:
            health_ok = await conn.health_check()
            validation_results["health_check"] = health_ok
            print(f"   健康检查: {'✅ 通过' if health_ok else '❌ 失败'}")
        except Exception as e:
            print(f"   健康检查: ❌ 失败 - {e}")
        
        # 3. 索引管理验证
        print("\n📋 3. 索引管理验证")
        try:
            # 检查索引是否存在
            exists_before = await conn.space_exists(test_space_name)
            print(f"   索引存在检查: {'✅ 通过' if not exists_before else '⚠️ 已存在'}")
            
            # 创建索引
            create_result = await conn.create_space(test_space_name, vector_size=768)
            print(f"   索引创建: {'✅ 通过' if create_result else '❌ 失败'}")
            
            # 再次检查索引是否存在
            exists_after = await conn.space_exists(test_space_name)
            print(f"   索引存在验证: {'✅ 通过' if exists_after else '❌ 失败'}")
            
            validation_results["space_management"] = all([create_result, exists_after])
        except Exception as e:
            print(f"   索引管理: ❌ 失败 - {e}")
        
        # 4. 文档CRUD验证
        print("\n📋 4. 文档CRUD验证")
        try:
            # 准备测试数据
            test_records = [
                {
                    "id": "test_doc_1",
                    "content": "这是一个测试文档，用于验证向量存储功能",
                    "title": "测试文档1",
                    "vector": [0.1] * 768,  # 模拟768维向量
                    "metadata": {"type": "test", "category": "validation"}
                },
                {
                    "id": "test_doc_2", 
                    "content": "这是另一个测试文档，包含不同的内容",
                    "title": "测试文档2",
                    "vector": [0.2] * 768,
                    "metadata": {"type": "test", "category": "validation"}
                }
            ]
            
            # 插入文档
            insert_errors = await conn.insert_records(test_space_name, test_records)
            insert_ok = len(insert_errors) == 0
            print(f"   文档插入: {'✅ 通过' if insert_ok else f'❌ 失败 - {insert_errors}'}")
            
            # 获取文档
            retrieved_doc = await conn.get_record([test_space_name], "test_doc_1")
            get_ok = retrieved_doc is not None and retrieved_doc.get("id") == "test_doc_1"
            print(f"   文档获取: {'✅ 通过' if get_ok else '❌ 失败'}")
            
            # 更新文档
            update_result = await conn.update_records(
                test_space_name,
                {"id": "test_doc_1"},
                {"title": "更新后的测试文档1", "updated": True}
            )
            print(f"   文档更新: {'✅ 通过' if update_result else '❌ 失败'}")
            
            # 删除文档
            delete_count = await conn.delete_records(test_space_name, {"id": ["test_doc_2"]})
            delete_ok = delete_count > 0
            print(f"   文档删除: {'✅ 通过' if delete_ok else '❌ 失败'} (删除数量: {delete_count})")
            
            # 如果删除失败，尝试删除第一个文档
            if not delete_ok:
                delete_count2 = await conn.delete_records(test_space_name, {"id": ["test_doc_1"]})
                delete_ok = delete_count2 > 0
                print(f"   备用删除: {'✅ 通过' if delete_ok else '❌ 失败'} (删除数量: {delete_count2})")
            
            validation_results["document_crud"] = all([insert_ok, get_ok, update_result, delete_ok])
        except Exception as e:
            print(f"   文档CRUD: ❌ 失败 - {e}")
        
        # 5. 搜索操作验证
        print("\n📋 5. 搜索操作验证")
        try:
            from app.infrastructure.vector_store.base import SearchRequest, MatchTextExpr, MatchDenseExpr
            
            # 文本搜索
            text_search_request = SearchRequest(
                condition={"metadata.type": "test"},
                match_exprs=[MatchTextExpr(
                    fields=["content", "title"],
                    matching_text="测试文档",
                    topn=10
                )],
                limit=5
            )
            
            text_search_result = await conn.search([test_space_name], text_search_request)
            text_search_ok = text_search_result is not None and "hits" in text_search_result
            print(f"   文本搜索: {'✅ 通过' if text_search_ok else '❌ 失败'}")
            
            # 向量搜索
            vector_search_request = SearchRequest(
                condition={"metadata.type": "test"},
                match_exprs=[MatchDenseExpr(
                    vector_column_name="vector",
                    embedding_data=[0.1] * 768,
                    embedding_data_type="float",
                    distance_type="cosine",
                    topn=5
                )],
                limit=5
            )
            
            vector_search_result = await conn.search([test_space_name], vector_search_request)
            vector_search_ok = vector_search_result is not None and "hits" in vector_search_result
            print(f"   向量搜索: {'✅ 通过' if vector_search_ok else '❌ 失败'}")
            
            # 测试搜索结果解析
            if text_search_ok:
                total = conn.get_total(text_search_result)
                chunk_ids = conn.get_chunk_ids(text_search_result)
                print(f"   搜索结果解析: ✅ 通过 (总数: {total}, 文档数: {len(chunk_ids)})")
            
            validation_results["search_operations"] = all([text_search_ok, vector_search_ok])
        except Exception as e:
            print(f"   搜索操作: ❌ 失败 - {e}")
            import traceback
            traceback.print_exc()
        
        # 6. SQL操作验证
        print("\n📋 6. SQL操作验证")
        try:
            # 简单的SQL查询
            sql_result = await conn.sql(
                "SELECT * FROM " + test_space_name + " LIMIT 1",
                fetch_size=1,
                format="json"
            )
            sql_ok = sql_result is not None
            print(f"   SQL查询: {'✅ 通过' if sql_ok else '❌ 失败'}")
            
            validation_results["sql_operations"] = sql_ok
        except Exception as e:
            print(f"   SQL操作: ❌ 失败 - {e}")
        
        # 清理测试数据
        print("\n🧹 清理测试数据")
        try:
            # 删除测试索引
            delete_result = await conn.delete_space(test_space_name)
            print(f"   测试索引清理: {'✅ 通过' if delete_result else '❌ 失败'}")
        except Exception as e:
            print(f"   测试索引清理: ❌ 失败 - {e}")
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        logging.exception("向量存储工厂验证异常")
    
    finally:
        # 注意：不关闭全局连接，因为其他模块可能还在使用
        print("ℹ️  保持全局向量存储连接开启，供其他模块使用")
    
    # 输出验证结果汇总
    print("\n" + "=" * 60)
    print("📊 向量存储工厂验证结果汇总")
    print("=" * 60)
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有向量存储功能验证通过！")
    else:
        print("⚠️  部分向量存储功能验证失败，请检查配置和连接")
    
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
        """运行向量存储工厂验证"""
        try:
            # 设置日志级别
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            print("🚀 启动向量存储工厂功能验证...")
            await validate_vector_store_factory()
            
        except KeyboardInterrupt:
            print("\n⏹️  验证被用户中断")
        except Exception as e:
            print(f"\n💥 验证过程中发生严重错误: {e}")
            logging.exception("向量存储工厂验证严重错误")
    
    # 运行验证
    asyncio.run(run_validation())