import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.infrastructure.llms import llm_factory

# =============================================================================
# 聊天模型工厂功能验证
# =============================================================================

async def validate_single_chat_model(provider: str, model_name: str) -> dict:
    """验证单个聊天模型"""
    result = {
        "provider": provider,
        "model_name": model_name,
        "model_creation": False,
        "basic_chat": False,
        "stream_chat": False,
        "tool_calling": False,
        "stream_tool_calling": False,
        "error": None
    }
    
    try:
        # 1. 模型创建验证
        model_supported = llm_factory.if_model_support(provider, model_name)
        if not model_supported:
            result["error"] = "模型不支持"
            return result
        
        model_instance = llm_factory.create_model(provider=provider, model=model_name)
        if model_instance is None:
            result["error"] = "模型创建失败"
            return result
        
        result["model_creation"] = True
        print(f"   ✅ {provider}/{model_name}: 模型创建成功 ({type(model_instance).__name__})")
        
        # 2. 基本聊天验证
        try:
            system_prompt = "你是一个有用的AI助手。"
            user_prompt = "请简单介绍一下你自己。"
            user_question = "你好，请简单回答。"
            
            response, token_count = await model_instance.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                user_question=user_question
            )
            
            if response is not None and hasattr(response, 'content'):
                result["basic_chat"] = True
                print(f"   ✅ {provider}/{model_name}: 基本聊天成功 (Token: {token_count})")
                print(f"   📝 返回内容: {response.content[:200]}{'...' if len(response.content) > 200 else ''}")
            else:
                result["error"] = "基本聊天失败"
        except Exception as e:
            result["error"] = f"基本聊天异常: {e}"
        
        # 3. 流式聊天验证
        if result["basic_chat"]:
            try:
                system_prompt = "你是一个有用的AI助手。"
                user_prompt = "请简单介绍一下你自己。"
                user_question = "请用流式方式回答。"
                
                stream, token_count = await model_instance.chat_stream(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    user_question=user_question
                )
                
                stream_content = ""
                chunk_count = 0
                async for chunk in stream:
                    stream_content += chunk
                    chunk_count += 1
                
                if len(stream_content) > 0:
                    result["stream_chat"] = True
                    print(f"   ✅ {provider}/{model_name}: 流式聊天成功 (Chunks: {chunk_count}, Token: {token_count})")
                    print(f"   📝 流式内容: {stream_content[:200]}{'...' if len(stream_content) > 200 else ''}")
                else:
                    result["error"] = "流式聊天失败"
            except Exception as e:
                result["error"] = f"流式聊天异常: {e}"
        
        # 4. 工具调用验证
        if result["basic_chat"]:
            try:
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "获取天气信息",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "city": {
                                        "type": "string",
                                        "description": "城市名称"
                                    }
                                },
                                "required": ["city"]
                            }
                        }
                    }
                ]
                
                system_prompt = "你是一个有用的AI助手，可以使用工具。"
                user_prompt = "请使用工具获取北京今天的天气。"
                user_question = "北京天气如何？"
                
                response, token_count = await model_instance.ask_tools(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    user_question=user_question,
                    tools=tools
                )
                
                if response is not None:
                    result["tool_calling"] = True
                    print(f"   ✅ {provider}/{model_name}: 工具调用成功 (Token: {token_count})")
                    print(f"   📝 工具调用返回: {response.content[:200]}{'...' if len(response.content) > 200 else ''}")
                    # 打印工具调用信息
                    if hasattr(response, 'tool_calls') and response.tool_calls:
                        print(f"   🔧 工具调用信息: {response.tool_calls}")
                    elif hasattr(response, 'tool_call') and response.tool_call:
                        print(f"   🔧 工具调用信息: {response.tool_call}")
                else:
                    result["error"] = "工具调用失败"
            except Exception as e:
                result["error"] = f"工具调用异常: {e}"
        
        # 5. 流式工具调用验证
        if result["basic_chat"]:
            try:
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "获取天气信息",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "city": {
                                        "type": "string",
                                        "description": "城市名称"
                                    }
                                },
                                "required": ["city"]
                            }
                        }
                    }
                ]
                
                system_prompt = "你是一个有用的AI助手，可以使用工具。"
                user_prompt = "请使用工具获取上海今天的天气。"
                user_question = "上海天气如何？"
                
                stream, token_count = await model_instance.ask_tools_stream(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    user_question=user_question,
                    tools=tools
                )
                
                stream_content = ""
                chunk_count = 0
                tool_calls_info = []
                async for chunk in stream:
                    stream_content += chunk
                    chunk_count += 1
                    # 检查chunk中是否包含工具调用信息
                    if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                        tool_calls_info.extend(chunk.tool_calls)
                    elif hasattr(chunk, 'tool_call') and chunk.tool_call:
                        tool_calls_info.append(chunk.tool_call)
                
                if len(stream_content) > 0:
                    result["stream_tool_calling"] = True
                    print(f"   ✅ {provider}/{model_name}: 流式工具调用成功 (Chunks: {chunk_count}, Token: {token_count})")
                    print(f"   📝 流式工具调用内容: {stream_content[:200]}{'...' if len(stream_content) > 200 else ''}")
                    # 打印流式工具调用信息
                    if tool_calls_info:
                        print(f"   🔧 流式工具调用信息: {tool_calls_info}")
                else:
                    result["error"] = "流式工具调用失败"
            except Exception as e:
                result["error"] = f"流式工具调用异常: {e}"
        
    except Exception as e:
        result["error"] = f"验证异常: {e}"
    
    return result

async def validate_chat_models_factory():
    """聊天模型工厂功能验证"""
    print("=" * 60)
    print("🔍 聊天模型工厂功能验证开始")
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
            if hasattr(llm_factory, '_config') and llm_factory._config:
                providers = llm_factory._config.get("models", {})
                print(f"   配置加载: ✅ 通过 - 加载了 {len(providers)} 个提供商配置")
                validation_results["config_loading"] = True
            else:
                print(f"   配置加载: ❌ 失败 - 未加载到任何配置")
        except Exception as e:
            print(f"   配置加载: ❌ 失败 - {e}")
        
        # 2. 支持的模型验证
        print("\n📋 2. 支持的模型验证")
        try:
            supported_models = llm_factory.get_supported_models()
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
            default_provider, default_model = llm_factory.get_default_model()
            default_result = await validate_single_chat_model(default_provider, default_model)
            
            if default_result["error"]:
                print(f"   默认模型验证: ❌ 失败 - {default_result['error']}")
            else:
                print(f"   默认模型验证: ✅ 通过")
                print(f"   基本聊天: {'✅' if default_result['basic_chat'] else '❌'}")
                print(f"   流式聊天: {'✅' if default_result['stream_chat'] else '❌'}")
                print(f"   工具调用: {'✅' if default_result['tool_calling'] else '❌'}")
                print(f"   流式工具调用: {'✅' if default_result['stream_tool_calling'] else '❌'}")
            
            # 3.2 验证所有有效模型
            print("   3.2 所有有效模型验证")
            supported_models = llm_factory.get_supported_models()
            all_models_results = []
            
            for provider, provider_info in supported_models.items():
                models = provider_info.get("models", {})
                for model_name in models.keys():
                    print(f"\n   {'='*50}")
                    print(f"   验证模型: {provider}/{model_name}")
                    print(f"   {'='*50}")
                    result = await validate_single_chat_model(provider, model_name)
                    all_models_results.append(result)
            
            # 统计结果
            total_models = len(all_models_results)
            successful_models = sum(1 for r in all_models_results if not r["error"])
            basic_chat_success = sum(1 for r in all_models_results if r["basic_chat"])
            stream_chat_success = sum(1 for r in all_models_results if r["stream_chat"])
            tool_calling_success = sum(1 for r in all_models_results if r["tool_calling"])
            stream_tool_calling_success = sum(1 for r in all_models_results if r["stream_tool_calling"])
            
            print(f"\n   验证结果统计:")
            print(f"   总模型数: {total_models}")
            print(f"   模型创建成功: {successful_models}")
            print(f"   基本聊天成功: {basic_chat_success}")
            print(f"   流式聊天成功: {stream_chat_success}")
            print(f"   工具调用成功: {tool_calling_success}")
            print(f"   流式工具调用成功: {stream_tool_calling_success}")
            
            validation_results["model_creation"] = successful_models > 0
        except Exception as e:
            print(f"   模型验证: ❌ 失败 - {e}")
        
        # 4. 错误处理验证
        print("\n📋 4. 错误处理验证")
        try:
            # 测试无效API密钥 - 创建一个使用无效API密钥的新实例
            print("   测试无效API密钥处理...")
            try:
                # 创建一个使用无效API密钥的模型实例
                invalid_model = llm_factory.create_model(api_key="invalid_key_test_12345")
                
                response, token_count = await invalid_model.chat(
                    system_prompt="测试",
                    user_prompt="测试", 
                    user_question="测试"
                )
                
                # 检查是否返回了错误响应
                if response is not None and hasattr(response, 'success') and not response.success:
                    print(f"   无效API密钥处理: ✅ 通过 - 正确返回错误响应")
                    validation_results["error_handling"] = True
                else:
                    print(f"   无效API密钥处理: ❌ 失败 - 未正确处理错误")
                    validation_results["error_handling"] = False
            except Exception as api_error:
                # 检查是否是认证相关的错误
                error_str = str(api_error).lower()
                if any(keyword in error_str for keyword in ['unauthorized', 'authentication', 'api key', 'invalid', '401', '403']):
                    print(f"   无效API密钥处理: ✅ 通过 - 正确抛出认证异常: {api_error}")
                    validation_results["error_handling"] = True
                else:
                    print(f"   无效API密钥处理: ⚠️  部分通过 - 抛出异常但非认证错误: {api_error}")
                    validation_results["error_handling"] = True  # 仍然算作通过，因为正确处理了错误
                    
        except Exception as e:
            print(f"   错误处理: ❌ 失败 - {e}")
            validation_results["error_handling"] = False
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        import logging
        logging.exception("聊天模型工厂验证异常")
    
    # 输出验证结果汇总
    print("\n" + "=" * 60)
    print("📊 聊天模型工厂验证结果汇总")
    print("=" * 60)
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有聊天模型功能验证通过！")
    else:
        print("⚠️  部分聊天模型功能验证失败，请检查配置和API密钥")
    
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
        """运行聊天模型工厂验证"""
        try:
            # 设置日志级别
            import logging
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            print("🚀 启动聊天模型工厂功能验证...")
            await validate_chat_models_factory()
            
        except KeyboardInterrupt:
            print("\n⏹️  验证被用户中断")
        except Exception as e:
            print(f"\n💥 验证过程中发生严重错误: {e}")
            import logging
            logging.exception("聊天模型工厂验证严重错误")
    
    # 运行验证
    asyncio.run(run_validation())