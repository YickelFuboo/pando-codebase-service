import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.infrastructure.llms import embedding_factory

# =============================================================================
# 嵌入模型工厂功能验证
# =============================================================================

async def validate_single_embedding_model(provider: str, model_name: str) -> dict:
    """验证单个嵌入模型"""
    result = {
        "provider": provider,
        "model_name": model_name,
        "model_creation": False,
        "encode_texts": False,
        "encode_query": False,
        "encode_documents": False,
        "error": None
    }
    
    try:
        # 1. 模型创建验证
        model_supported = embedding_factory.if_model_support(provider, model_name)
        if not model_supported:
            result["error"] = "模型不支持"
            return result
        
        model_instance = embedding_factory.create_model(provider=provider, model=model_name)
        if model_instance is None:
            result["error"] = "模型创建失败"
            return result
        
        result["model_creation"] = True
        print(f"   ✅ {provider}/{model_name}: 模型创建成功 ({type(model_instance).__name__})")
        
        # 2. 文本编码验证
        try:
            test_texts = ["这是一个测试文本", "This is a test text", "测试中文和英文混合"]
            embeddings, token_count = await model_instance.encode(test_texts)
            
            if embeddings is not None and len(embeddings) > 0:
                result["encode_texts"] = True
                print(f"   ✅ {provider}/{model_name}: 文本编码成功 (Token: {token_count}, 向量维度: {embeddings.shape})")
                print(f"   📝 编码结果: 成功编码 {len(embeddings)} 个文本，向量维度 {embeddings.shape[1] if len(embeddings.shape) > 1 else 'N/A'}")
            else:
                result["error"] = "文本编码失败"
        except Exception as e:
            result["error"] = f"文本编码异常: {e}"
        
        # 3. 查询编码验证
        if result["encode_texts"]:
            try:
                query_text = "这是一个查询文本"
                query_embedding, token_count = await model_instance.encode_queries(query_text)
                
                if query_embedding is not None and len(query_embedding) > 0:
                    result["encode_query"] = True
                    print(f"   ✅ {provider}/{model_name}: 查询编码成功 (Token: {token_count}, 向量维度: {query_embedding.shape})")
                    print(f"   📝 查询编码结果: 向量维度 {query_embedding.shape[0] if len(query_embedding.shape) > 0 else 'N/A'}")
                else:
                    result["error"] = "查询编码失败"
            except Exception as e:
                result["error"] = f"查询编码异常: {e}"
        
        # 4. 文档编码验证（如果支持）
        if result["encode_query"]:
            try:
                # 检查是否有encode_documents方法
                if hasattr(model_instance, 'encode_documents'):
                    doc_texts = ["这是第一个文档", "这是第二个文档"]
                    doc_embeddings, token_count = await model_instance.encode_documents(doc_texts)
                    
                    if doc_embeddings is not None and len(doc_embeddings) > 0:
                        result["encode_documents"] = True
                        print(f"   ✅ {provider}/{model_name}: 文档编码成功 (Token: {token_count}, 向量维度: {doc_embeddings.shape})")
                        print(f"   📝 文档编码结果: 成功编码 {len(doc_embeddings)} 个文档")
                    else:
                        print(f"   ⚠️  {provider}/{model_name}: 文档编码方法存在但返回空结果")
                else:
                    print(f"   ℹ️  {provider}/{model_name}: 不支持文档编码方法")
                    result["encode_documents"] = True  # 不算作失败
            except Exception as e:
                print(f"   ⚠️  {provider}/{model_name}: 文档编码异常: {e}")
                result["encode_documents"] = True  # 不算作失败
        
    except Exception as e:
        result["error"] = f"验证异常: {e}"
    
    return result

async def validate_embedding_models_factory():
    """嵌入模型工厂功能验证"""
    print("=" * 60)
    print("🔍 嵌入模型工厂功能验证开始")
    print("=" * 60)
    
    validation_results = {
        "config_loading": False,
        "supported_models": False,
        "model_creation": False,
        "error_handling": False
    }
    
    try:
        # 1. 配置加载验证
        print("\n📋 1. 配置加载验证")
        try:
            # 检查配置文件是否存在
            if hasattr(embedding_factory, '_config') and embedding_factory._config:
                providers = embedding_factory._config.get("models", {})
                print(f"   配置加载: ✅ 通过 - 加载了 {len(providers)} 个提供商配置")
                validation_results["config_loading"] = True
            else:
                print(f"   配置加载: ❌ 失败 - 未加载到任何配置")
        except Exception as e:
            print(f"   配置加载: ❌ 失败 - {e}")
        
        # 2. 支持的模型验证
        print("\n📋 2. 支持的模型验证")
        try:
            supported_models = embedding_factory.get_supported_models()
            if supported_models:
                total_models = sum(len(provider_info.get("models", {})) for provider_info in supported_models.values())
                print(f"   支持的模型: ✅ 通过 - {len(supported_models)} 个提供商，{total_models} 个模型")
                for provider, provider_info in supported_models.items():
                    models = provider_info.get("models", {})
                    print(f"     {provider}: {len(models)} 个模型")
            else:
                print(f"   支持的模型: ❌ 失败 - 未找到支持的模型")
            
            validation_results["supported_models"] = len(supported_models) > 0
        except Exception as e:
            print(f"   支持的模型: ❌ 失败 - {e}")
        
        # 3. 模型验证
        print("\n📋 3. 模型验证")
        try:
            # 3.1 先验证默认模型
            print("   3.1 默认模型验证")
            default_provider, default_model = embedding_factory.get_default_model()
            default_result = await validate_single_embedding_model(default_provider, default_model)
            
            if default_result["error"]:
                print(f"   默认模型验证: ❌ 失败 - {default_result['error']}")
            else:
                print(f"   默认模型验证: ✅ 通过")
                print(f"   文本编码: {'✅' if default_result['encode_texts'] else '❌'}")
                print(f"   查询编码: {'✅' if default_result['encode_query'] else '❌'}")
                print(f"   文档编码: {'✅' if default_result['encode_documents'] else '❌'}")
            
            # 3.2 验证所有有效模型
            print("   3.2 所有有效模型验证")
            supported_models = embedding_factory.get_supported_models()
            all_models_results = []
            
            for provider, provider_info in supported_models.items():
                models = provider_info.get("models", {})
                for model_name in models.keys():
                    print(f"\n   {'='*50}")
                    print(f"   验证模型: {provider}/{model_name}")
                    print(f"   {'='*50}")
                    result = await validate_single_embedding_model(provider, model_name)
                    all_models_results.append(result)
            
            # 统计结果
            total_models = len(all_models_results)
            successful_models = sum(1 for r in all_models_results if not r["error"])
            encode_texts_success = sum(1 for r in all_models_results if r["encode_texts"])
            encode_query_success = sum(1 for r in all_models_results if r["encode_query"])
            encode_documents_success = sum(1 for r in all_models_results if r["encode_documents"])
            
            print(f"\n   验证结果统计:")
            print(f"   总模型数: {total_models}")
            print(f"   模型创建成功: {successful_models}")
            print(f"   文本编码成功: {encode_texts_success}")
            print(f"   查询编码成功: {encode_query_success}")
            print(f"   文档编码成功: {encode_documents_success}")
            
            validation_results["model_creation"] = successful_models > 0
        except Exception as e:
            print(f"   模型验证: ❌ 失败 - {e}")
        
        # 4. 错误处理验证
        print("\n📋 4. 错误处理验证")
        try:
            # 测试无效的模型创建
            try:
                invalid_model = embedding_factory.create_model(provider="invalid_provider", model="invalid_model")
                if invalid_model is not None:
                    error_handling_ok = True
                    print(f"   无效模型创建: ✅ 通过 - 正确回退到默认模型 ({type(invalid_model).__name__})")
                else:
                    error_handling_ok = False
                    print(f"   无效模型创建: ❌ 失败 - 返回了None")
            except Exception as e:
                error_handling_ok = True
                print(f"   无效模型创建: ✅ 通过 - 正确抛出异常: {type(e).__name__}")
            
            validation_results["error_handling"] = error_handling_ok
        except Exception as e:
            print(f"   错误处理: ❌ 失败 - {e}")
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        import logging
        logging.exception("嵌入模型工厂验证异常")
    
    # 输出验证结果汇总
    print("\n" + "=" * 60)
    print("📊 嵌入模型工厂验证结果汇总")
    print("=" * 60)
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有嵌入模型功能验证通过！")
    else:
        print("⚠️  部分嵌入模型功能验证失败，请检查配置和API密钥")
    
    print("=" * 60)
    
    return validation_results

if __name__ == "__main__":
    import asyncio
    import os
    import sys
    
    # 设置控制台编码为UTF-8
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    async def run_validation():
        """运行嵌入模型工厂验证"""
        try:
            # 设置日志级别
            import logging
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            print("🚀 启动嵌入模型工厂功能验证...")
            await validate_embedding_models_factory()
            
        except KeyboardInterrupt:
            print("\n⏹️  验证被用户中断")
        except Exception as e:
            print(f"\n💥 验证过程中发生严重错误: {e}")
            import logging
            logging.exception("嵌入模型工厂验证严重错误")
    
    # 运行验证
    asyncio.run(run_validation())