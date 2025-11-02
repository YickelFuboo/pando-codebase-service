

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.infrastructure.storage.factory import STORAGE_CONN

# =============================================================================
# 存储工厂功能验证
# =============================================================================

async def validate_storage_factory():
    """存储工厂功能验证"""
    print("=" * 60)
    print("🔍 存储工厂功能验证开始")
    print("=" * 60)
    
    validation_results = {
        "connection": False,
        "health_check": False,
        "file_upload": False,
        "file_download": False,
        "file_exists": False,
        "file_metadata": False,
        "file_url": False,
        "file_delete": False
    }
    
    conn = None
    test_file_index = "test_storage_file.txt"
    test_bucket_name = "test-storage-bucket"
    
    try:
        # 1. 连接创建验证
        print("\n📋 1. 连接创建验证")
        try:
            # 使用全局连接
            global STORAGE_CONN
            conn = STORAGE_CONN
            
            if conn is None:
                print(f"   连接创建: ❌ 失败 - 全局连接未初始化")
                return validation_results
            
            validation_results["connection"] = True
            print(f"   连接创建: ✅ 通过")
            print(f"   存储类型: {type(conn).__name__}")
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
        
        if not health_ok:
            print("   ⚠️  存储服务不健康，跳过其他验证")
            return validation_results
        
        # 3. 文件上传验证
        print("\n📋 3. 文件上传验证")
        try:
            import io
            
            # 准备测试文件数据
            test_content = "这是一个测试文件，用于验证存储功能。\n测试时间: " + str(datetime.now())
            test_content_bytes = test_content.encode('utf-8')
            test_file_data = io.BytesIO(test_content_bytes)
            
            # 上传文件
            file_id = await conn.put(
                file_index=test_file_index,
                file_data=test_file_data,
                bucket_name=test_bucket_name,
                content_type="text/plain",
                metadata={"test": "true", "created_by": "validation"}
            )
            
            upload_ok = file_id == test_file_index
            validation_results["file_upload"] = upload_ok
            print(f"   文件上传: {'✅ 通过' if upload_ok else '❌ 失败'}")
            print(f"   文件ID: {file_id}")
        except Exception as e:
            print(f"   文件上传: ❌ 失败 - {e}")
        
        # 4. 文件存在检查验证
        print("\n📋 4. 文件存在检查验证")
        try:
            exists = await conn.exists(test_file_index, test_bucket_name)
            validation_results["file_exists"] = exists
            print(f"   文件存在检查: {'✅ 通过' if exists else '❌ 失败'}")
        except Exception as e:
            print(f"   文件存在检查: ❌ 失败 - {e}")
        
        # 5. 文件下载验证
        print("\n📋 5. 文件下载验证")
        try:
            downloaded_data = await conn.get(test_file_index, test_bucket_name)
            download_ok = downloaded_data is not None
            
            if download_ok:
                # 读取下载的内容
                content = downloaded_data.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                print(f"   下载内容长度: {len(content)} 字符")
                print(f"   内容预览: {content[:50]}...")
            
            validation_results["file_download"] = download_ok
            print(f"   文件下载: {'✅ 通过' if download_ok else '❌ 失败'}")
        except Exception as e:
            print(f"   文件下载: ❌ 失败 - {e}")
        
        # 6. 文件元数据验证
        print("\n📋 6. 文件元数据验证")
        try:
            metadata = await conn.get_metadata(test_file_index, test_bucket_name)
            metadata_ok = metadata is not None and isinstance(metadata, dict)
            
            if metadata_ok:
                print(f"   文件大小: {metadata.get('file_size', 'N/A')} 字节")
                print(f"   内容类型: {metadata.get('content_type', 'N/A')}")
                print(f"   最后修改: {metadata.get('last_modified', 'N/A')}")
                print(f"   自定义元数据: {metadata.get('metadata', {})}")
            
            validation_results["file_metadata"] = metadata_ok
            print(f"   文件元数据: {'✅ 通过' if metadata_ok else '❌ 失败'}")
        except Exception as e:
            print(f"   文件元数据: ❌ 失败 - {e}")
        
        # 7. 文件URL验证
        print("\n📋 7. 文件URL验证")
        try:
            file_url = await conn.get_url(test_file_index, test_bucket_name, expires_in=3600)
            url_ok = file_url is not None and isinstance(file_url, str) and file_url.startswith(('http://', 'https://'))
            
            if url_ok:
                print(f"   文件URL: {file_url[:80]}...")
            
            validation_results["file_url"] = url_ok
            print(f"   文件URL: {'✅ 通过' if url_ok else '❌ 失败'}")
        except Exception as e:
            print(f"   文件URL: ❌ 失败 - {e}")
        
        # 8. 文件删除验证
        print("\n📋 8. 文件删除验证")
        try:
            delete_result = await conn.delete(test_file_index, test_bucket_name)
            validation_results["file_delete"] = delete_result
            print(f"   文件删除: {'✅ 通过' if delete_result else '❌ 失败'}")
            
            # 验证文件确实被删除
            if delete_result:
                still_exists = await conn.exists(test_file_index, test_bucket_name)
                print(f"   删除验证: {'✅ 通过' if not still_exists else '❌ 失败 - 文件仍然存在'}")
        except Exception as e:
            print(f"   文件删除: ❌ 失败 - {e}")
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        logging.exception("存储工厂验证异常")
    
    # 输出验证结果汇总
    print("\n" + "=" * 60)
    print("📊 存储工厂验证结果汇总")
    print("=" * 60)
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有存储功能验证通过！")
    else:
        print("⚠️  部分存储功能验证失败，请检查配置和连接")
    
    print("=" * 60)
    
    return validation_results

if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    import sys
    
    # 设置控制台编码为UTF-8
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    async def run_validation():
        """运行存储工厂验证"""
        try:
            # 设置日志级别
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            print("🚀 启动存储工厂功能验证...")
            await validate_storage_factory()
            
        except KeyboardInterrupt:
            print("\n⏹️  验证被用户中断")
        except Exception as e:
            print(f"\n💥 验证过程中发生严重错误: {e}")
            logging.exception("存储工厂验证严重错误")
        finally:
            # 清理资源
            try:
                if STORAGE_CONN and hasattr(STORAGE_CONN, 'close'):
                    await STORAGE_CONN.close()
                    print("🔒 存储连接已关闭")
            except Exception as e:
                print(f"⚠️  关闭存储连接时出错: {e}")
    
    # 运行验证
    asyncio.run(run_validation())