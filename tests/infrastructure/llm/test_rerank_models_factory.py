import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.infrastructure.llms import rerank_factory

# =============================================================================
# 嵌入模型工厂功能验证
# =============================================================================

async def validate_single_rerank_model(provider: str, model_name: str) -> dict:
    """
    验证单个重排序模型的功能
    
    Args:
        provider (str): 提供商名称
        model_name (str): 模型名称
        
    Returns:
        dict: 验证结果
    """
    result = {
        "provider": provider,
        "model_name": model_name,
        "model_creation": False,
        "similarity": False,
        "error": None
    }
    
    try:
        # 1. 模型创建验证
        try:
            model_instance = rerank_factory.create_model(provider, model_name)
            if model_instance:
                result["model_creation"] = True
                print(f"   ✅ {provider}/{model_name}: 模型创建成功 ({model_instance.__class__.__name__})")
            else:
                result["error"] = "模型创建失败"
                return result
        except Exception as e:
            result["error"] = f"模型创建异常: {e}"
            return result
        
        # 2. 相似度计算验证
        try:
            query = "什么是人工智能？"
            test_texts = [
                "人工智能是计算机科学的一个分支",
                "机器学习是人工智能的重要组成部分",
                "深度学习是机器学习的一个子领域"
            ]
            
            scores, token_count = await model_instance.similarity(query, test_texts)
            if scores is not None and len(scores) > 0:
                result["similarity"] = True
                print(f"   ✅ {provider}/{model_name}: 相似度计算成功 (Token: {token_count}, 分数: {scores.shape})")
                print(f"   📝 相似度分数: {scores[:3] if len(scores) >= 3 else scores}")
            else:
                result["error"] = "相似度计算失败"
        except Exception as e:
            result["error"] = f"相似度计算异常: {e}"
            
    except Exception as e:
        result["error"] = f"验证异常: {e}"
    
    return result


async def validate_rerank_models_factory():
    """
    验证重排序模型工厂的完整功能
    """
    print("🚀 启动重排序模型工厂功能验证...")
    print("=" * 60)
    print("🔍 重排序模型工厂功能验证开始")
    print("=" * 60)
    
    validation_results = {
        "config_loading": False,
        "supported_models": False,
        "model_creation": False,
        "error_handling": False
    }
    
    # 1. 配置加载验证
    print("\n📋 1. 配置加载验证")
    try:
        if hasattr(rerank_factory, '_config') and rerank_factory._config:
            providers = rerank_factory._config.get("models", {})
            print(f"   配置加载: ✅ 通过 - 加载了 {len(providers)} 个提供商配置")
            validation_results["config_loading"] = True
        else:
            print(f"   配置加载: ❌ 失败 - 未加载到任何配置")
    except Exception as e:
        print(f"   配置加载: ❌ 失败 - {e}")
    
    # 2. 支持的模型验证
    print("\n📋 2. 支持的模型验证")
    try:
        supported_models = rerank_factory.get_supported_models()
        total_providers = len(supported_models)
        total_models = sum(len(provider_info.get("models", {})) for provider_info in supported_models.values())
        
        if total_providers > 0 and total_models > 0:
            print(f"   支持的模型: ✅ 通过 - {total_providers} 个提供商，{total_models} 个模型")
            for provider, provider_info in supported_models.items():
                models = provider_info.get("models", {})
                print(f"     {provider}: {len(models)} 个模型")
            validation_results["supported_models"] = True
        else:
            print(f"   支持的模型: ❌ 失败 - 未找到支持的模型")
    except Exception as e:
        print(f"   支持的模型: ❌ 失败 - {e}")
    
    # 3. 模型验证
    print("\n📋 3. 模型验证")
    
    # 3.1 默认模型验证
    print("   3.1 默认模型验证")
    try:
        default_provider = rerank_factory._config.get("default", {}).get("provider")
        default_model = rerank_factory._config.get("default", {}).get("model")
        
        if default_provider and default_model:
            print(f"   默认模型: {default_provider}/{default_model}")
            default_result = await validate_single_rerank_model(default_provider, default_model)
            validation_results["model_creation"] = default_result["model_creation"]
        else:
            print("   默认模型: ❌ 未配置")
            default_result = {"error": "未配置默认模型"}
    except Exception as e:
        print(f"   默认模型验证: ❌ 失败 - {e}")
        default_result = {"error": str(e)}
    
    # 3.2 所有有效模型验证
    print("   3.2 所有有效模型验证")
    supported_models = rerank_factory.get_supported_models()
    all_models_results = []
    
    for provider, provider_info in supported_models.items():
        models = provider_info.get("models", {})
        for model_name in models.keys():
            print(f"\n   {'='*50}")
            print(f"   验证模型: {provider}/{model_name}")
            print(f"   {'='*50}")
            result = await validate_single_rerank_model(provider, model_name)
            all_models_results.append(result)
    
    # 统计结果
    print(f"\n   验证结果统计:")
    print(f"   总模型数: {len(all_models_results)}")
    model_creation_success = sum(1 for r in all_models_results if r["model_creation"])
    similarity_success = sum(1 for r in all_models_results if r["similarity"])
    print(f"   模型创建成功: {model_creation_success}")
    print(f"   相似度计算成功: {similarity_success}")
    
    # 默认模型结果
    if default_result["error"]:
        print(f"   默认模型验证: ❌ 失败 - {default_result['error']}")
    else:
        print(f"   默认模型验证: ✅ 通过")
        print(f"   模型创建: {'✅' if default_result['model_creation'] else '❌'}")
        print(f"   相似度计算: {'✅' if default_result['similarity'] else '❌'}")
    
    # 4. 错误处理验证
    print("\n📋 4. 错误处理验证")
    try:
        print("   测试无效模型创建...")
        try:
            invalid_model = rerank_factory.create_model("invalid_provider", "invalid_model")
            if invalid_model is not None:
                print(f"   无效模型创建: ✅ 通过 - 正确回退到默认模型 ({type(invalid_model).__name__})")
                validation_results["error_handling"] = True
            else:
                print(f"   无效模型创建: ❌ 失败 - 返回了None")
                validation_results["error_handling"] = False
        except Exception as invalid_error:
            print(f"   无效模型创建: ✅ 通过 - 正确抛出异常: {invalid_error}")
            validation_results["error_handling"] = True
    except Exception as e:
        print(f"   错误处理: ❌ 失败 - {e}")
        validation_results["error_handling"] = False
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 重排序模型工厂验证结果汇总")
    print("=" * 60)
    
    for key, value in validation_results.items():
        status = "✅ 通过" if value else "❌ 失败"
        print(f"   {key}: {status}")
    
    passed_tests = sum(validation_results.values())
    total_tests = len(validation_results)
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有重排序模型功能验证通过！")
    else:
        print("⚠️  部分重排序模型功能验证失败，请检查上述错误信息")
    
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
    
    asyncio.run(validate_rerank_models_factory())
