import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.infrastructure.llms import cv_factory

# =============================================================================
# 计算机视觉模型工厂功能验证
# =============================================================================

async def validate_single_cv_model(provider: str, model_name: str) -> dict:
    """验证单个CV模型"""
    result = {
        "provider": provider,
        "model_name": model_name,
        "model_creation": False,
        "image_processing": False,
        "image_describe": False,
        "image_describe_with_prompt": False,
        "image_chat": False,
        "stream_chat": False,
        "error": None
    }
    
    try:
        # 1. 模型创建验证
        model_supported = cv_factory.if_model_support(provider, model_name)
        if not model_supported:
            result["error"] = "模型不支持"
            return result
        
        model_instance = cv_factory.create_model(provider=provider, model=model_name)
        if model_instance is None:
            result["error"] = "模型创建失败"
            return result
        
        result["model_creation"] = True
        print(f"   ✅ {provider}/{model_name}: 模型创建成功 ({type(model_instance).__name__})")
        
        # 2. 图像处理验证
        try:
            # 创建一个简单的测试图像（1x1像素的PNG）
            import base64
            from io import BytesIO
            from PIL import Image
            
            # 创建一个32x32像素的测试图像（满足Qwen-VL系列的最小尺寸要求）
            test_image = Image.new('RGB', (32, 32), color='red')
            test_image_bytes = BytesIO()
            test_image.save(test_image_bytes, format='PNG')
            test_image_bytes.seek(0)
            
            # 转换为base64字符串用于chat方法
            test_image_b64 = base64.b64encode(test_image_bytes.getvalue()).decode('utf-8')
            
            # 测试图像描述
            description, token_count = await model_instance.describe(test_image_bytes)
            if description:
                result["image_processing"] = True
                result["image_describe"] = True
                print(f"   ✅ {provider}/{model_name}: 图像描述成功")
                print(f"   📝 图像描述内容: {description[:200]}{'...' if len(description) > 200 else ''}")
            else:
                result["error"] = "图像描述失败"
        except Exception as e:
            result["error"] = f"图像处理异常: {e}"
        
        # 3. 测试自定义提示词图像描述
        if result["image_processing"]:
            try:
                custom_prompt = "请详细分析这张图片中的颜色、形状和可能的用途。"
                description_with_prompt, token_count = await model_instance.describe_with_prompt(test_image_bytes, custom_prompt)
                if description_with_prompt:
                    result["image_describe_with_prompt"] = True
                    print(f"   ✅ {provider}/{model_name}: 自定义提示词图像描述成功")
                    print(f"   📝 自定义提示词描述内容: {description_with_prompt[:200]}{'...' if len(description_with_prompt) > 200 else ''}")
                else:
                    result["error"] = "自定义提示词图像描述失败"
            except Exception as e:
                result["error"] = f"自定义提示词图像描述异常: {e}"
        
        # 4. 图像聊天验证
        if result["image_processing"]:
            try:
                system = "你是一个有用的AI助手，可以分析图像内容。"
                history = [{"role": "user", "content": "请分析这张图片"}]
                gen_conf = {"temperature": 0.3, "top_p": 0.7}
                response, token_count = await model_instance.chat(system, history, gen_conf, test_image_b64)
                if response:
                    result["image_chat"] = True
                    print(f"   ✅ {provider}/{model_name}: 图像聊天成功 (Token: {token_count})")
                    print(f"   📝 图像聊天返回: {response[:200]}{'...' if len(response) > 200 else ''}")
                else:
                    result["error"] = "图像聊天失败"
            except Exception as e:
                result["error"] = f"图像聊天异常: {e}"
        
        # 5. 流式聊天验证
        if result["image_chat"]:
            try:
                system = "你是一个有用的AI助手，可以分析图像内容。"
                history = [{"role": "user", "content": "请分析这张图片"}]
                gen_conf = {"temperature": 0.3, "top_p": 0.7}
                stream_content = ""
                final_token_count = 0
                
                async for content, token_count in model_instance.chat_stream(system, history, gen_conf, test_image_b64):
                    stream_content += content
                    final_token_count = token_count
                
                if len(stream_content) > 0:
                    result["stream_chat"] = True
                    print(f"   ✅ {provider}/{model_name}: 流式聊天成功 (Token: {final_token_count})")
                    print(f"   📝 流式聊天内容: {stream_content[:200]}{'...' if len(stream_content) > 200 else ''}")
                else:
                    result["stream_chat"] = False
                    print(f"   ❌ {provider}/{model_name}: 流式聊天失败 - 无内容返回")
            except Exception as e:
                result["stream_chat"] = False
                print(f"   ❌ {provider}/{model_name}: 流式聊天异常: {e}")
        
    except Exception as e:
        result["error"] = f"验证异常: {e}"
    
    return result

async def validate_cv_models_factory():
    """计算机视觉模型工厂功能验证"""
    print("=" * 60)
    print("🔍 计算机视觉模型工厂功能验证开始")
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
            if hasattr(cv_factory, '_config') and cv_factory._config:
                providers = cv_factory._config.get("models", {})
                print(f"   配置加载: ✅ 通过 - 加载了 {len(providers)} 个提供商配置")
                validation_results["config_loading"] = True
            else:
                print(f"   配置加载: ❌ 失败 - 未加载到任何配置")
        except Exception as e:
            print(f"   配置加载: ❌ 失败 - {e}")
        
        # 2. 支持的模型验证
        print("\n📋 2. 支持的模型验证")
        try:
            supported_models = cv_factory.get_supported_models()
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
            default_provider, default_model = cv_factory.get_default_model()
            default_result = await validate_single_cv_model(default_provider, default_model)
            
            if default_result["error"]:
                print(f"   默认模型验证: ❌ 失败 - {default_result['error']}")
            else:
                print(f"   默认模型验证: ✅ 通过")
                print(f"   图像处理: {'✅' if default_result['image_processing'] else '❌'}")
                print(f"   图像描述: {'✅' if default_result['image_describe'] else '❌'}")
                print(f"   自定义提示词图像描述: {'✅' if default_result['image_describe_with_prompt'] else '❌'}")
                print(f"   图像聊天: {'✅' if default_result['image_chat'] else '❌'}")
                print(f"   流式聊天: {'✅' if default_result['stream_chat'] else '❌'}")
            
            # 3.2 验证所有有效模型
            print("   3.2 所有有效模型验证")
            supported_models = cv_factory.get_supported_models()
            all_models_results = []
            
            for provider, provider_info in supported_models.items():
                models = provider_info.get("models", {})
                for model_name in models.keys():
                    print(f"\n   {'='*50}")
                    print(f"   验证模型: {provider}/{model_name}")
                    print(f"   {'='*50}")
                    result = await validate_single_cv_model(provider, model_name)
                    all_models_results.append(result)
            
            # 统计结果
            total_models = len(all_models_results)
            successful_models = sum(1 for r in all_models_results if not r["error"])
            image_processing_success = sum(1 for r in all_models_results if r["image_processing"])
            image_describe_success = sum(1 for r in all_models_results if r["image_describe"])
            image_describe_with_prompt_success = sum(1 for r in all_models_results if r["image_describe_with_prompt"])
            image_chat_success = sum(1 for r in all_models_results if r["image_chat"])
            stream_chat_success = sum(1 for r in all_models_results if r["stream_chat"])
            
            print(f"\n   验证结果统计:")
            print(f"   总模型数: {total_models}")
            print(f"   模型创建成功: {successful_models}")
            print(f"   图像处理成功: {image_processing_success}")
            print(f"   图像描述成功: {image_describe_success}")
            print(f"   自定义提示词图像描述成功: {image_describe_with_prompt_success}")
            print(f"   图像聊天成功: {image_chat_success}")
            print(f"   流式聊天成功: {stream_chat_success}")
            
            validation_results["model_creation"] = successful_models > 0
        except Exception as e:
            print(f"   模型验证: ❌ 失败 - {e}")
        
        # 4. 错误处理验证
        print("\n📋 4. 错误处理验证")
        try:
            # 测试无效的模型创建 - 工厂应该回退到默认模型
            try:
                invalid_model = cv_factory.create_model(provider="invalid_provider", model="invalid_model")
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
        logging.exception("CV模型工厂验证异常")
    
    # 输出验证结果汇总
    print("\n" + "=" * 60)
    print("📊 计算机视觉模型工厂验证结果汇总")
    print("=" * 60)
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有CV模型功能验证通过！")
    else:
        print("⚠️  部分CV模型功能验证失败，请检查配置和API密钥")
    
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
        """运行CV模型工厂验证"""
        try:
            # 设置日志级别
            import logging
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            print("🚀 启动CV模型工厂功能验证...")
            await validate_cv_models_factory()
            
        except KeyboardInterrupt:
            print("\n⏹️  验证被用户中断")
        except Exception as e:
            print(f"\n💥 验证过程中发生严重错误: {e}")
            import logging
            logging.exception("CV模型工厂验证严重错误")
    
    # 运行验证
    asyncio.run(run_validation())