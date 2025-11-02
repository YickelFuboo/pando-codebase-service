import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.infrastructure.llms import stt_factory

# =============================================================================
# 嵌入模型工厂功能验证
# =============================================================================

async def validate_single_stt_model(provider: str, model_name: str) -> dict:
    """
    验证单个STT模型的功能
    
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
        "stt": False,
        "error": None
    }
    
    try:
        # 1. 模型创建验证
        try:
            model_instance = stt_factory.create_model(provider, model_name)
            if model_instance:
                result["model_creation"] = True
                print(f"   ✅ {provider}/{model_name}: 模型创建成功 ({model_instance.__class__.__name__})")
            else:
                result["error"] = "模型创建失败"
                return result
        except Exception as e:
            result["error"] = f"模型创建异常: {e}"
            return result
        
        # 2. STT功能验证
        try:
            # 创建一个简单的测试音频文件（模拟）
            import io
            import wave
            import struct
            import tempfile
            import os
            
            # 创建一个简单的WAV文件（1秒的静音）
            sample_rate = 16000
            duration = 1  # 1秒
            num_samples = sample_rate * duration
            
            # 创建简单的音频数据（正弦波，模拟语音）
            import math
            frequency = 440  # 440Hz，A4音符
            audio_samples = []
            for i in range(num_samples):
                # 生成正弦波，幅度逐渐减小
                amplitude = int(16000 * 0.1 * math.sin(2 * math.pi * frequency * i / sample_rate))
                audio_samples.append(amplitude)
            
            audio_data = struct.pack('<' + 'h' * num_samples, *audio_samples)
            
            # 创建WAV文件头
            wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
                b'RIFF',
                36 + len(audio_data),
                b'WAVE',
                b'fmt ',
                16,  # fmt chunk size
                1,   # audio format (PCM)
                1,   # number of channels
                sample_rate,
                sample_rate * 2,  # byte rate
                2,   # block align
                16,  # bits per sample
                b'data',
                len(audio_data)
            )
            
            # 组合完整的WAV文件
            wav_data = wav_header + audio_data
            
            # 尝试不同的音频输入方式
            test_audio = None
            temp_file_path = None
            
            # 对于qwen模型，优先尝试URL方式（模拟）
            if provider == "qwen":
                try:
                    # 方式1: 尝试使用阿里云官方测试音频URL
                    test_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
                    text, token_count = await model_instance.stt(test_url)
                    if text is not None and not text.startswith("**ERROR**"):
                        result["stt"] = True
                        print(f"   ✅ {provider}/{model_name}: URL方式STT转换成功 (Token: {token_count})")
                        print(f"   📝 转录结果: {text[:100]}{'...' if len(text) > 100 else ''}")
                        return result
                    else:
                        print(f"   ❌ {provider}/{model_name}: URL方式STT转换失败 - {text}")
                except Exception as e1:
                    print(f"   ⚠️  URL方式失败: {e1}")
                
                # qwen模型只支持URL和本地文件方式，跳过其他方式测试
                print(f"   ℹ️  {provider}/{model_name}: 通义千问ASR模型只支持URL和本地文件方式")
                result["error"] = "通义千问ASR模型只支持URL和本地文件方式，不支持BytesIO和字节数据"
                return result
            
            # 其他模型支持多种方式
            try:
                # 方式2: 尝试使用BytesIO
                test_audio = io.BytesIO(wav_data)
                text, token_count = await model_instance.stt(test_audio)
                if text is not None and not text.startswith("**ERROR**"):
                    result["stt"] = True
                    print(f"   ✅ {provider}/{model_name}: STT转换成功 (Token: {token_count})")
                    print(f"   📝 转录结果: {text[:100]}{'...' if len(text) > 100 else ''}")
                    return result
                else:
                    print(f"   ❌ {provider}/{model_name}: BytesIO方式 STT转换失败 - {text}")
            except Exception as e2:
                print(f"   ⚠️  BytesIO方式失败: {e2}")
            
            try:
                # 方式3: 尝试使用临时文件
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(wav_data)
                    temp_file_path = temp_file.name
                
                text, token_count = await model_instance.stt(temp_file_path)
                if text is not None and not text.startswith("**ERROR**"):
                    result["stt"] = True
                    print(f"   ✅ {provider}/{model_name}: STT转换成功 (Token: {token_count})")
                    print(f"   📝 转录结果: {text[:100]}{'...' if len(text) > 100 else ''}")
                    return result
                else:
                    print(f"   ❌ {provider}/{model_name}: 临时文件方式 STT转换失败 - {text}")
            except Exception as e3:
                print(f"   ⚠️  临时文件方式失败: {e3}")
            
            try:
                # 方式4: 尝试使用字节数据
                text, token_count = await model_instance.stt(wav_data)
                if text is not None and not text.startswith("**ERROR**"):
                    result["stt"] = True
                    print(f"   ✅ {provider}/{model_name}: STT转换成功 (Token: {token_count})")
                    print(f"   📝 转录结果: {text[:100]}{'...' if len(text) > 100 else ''}")
                    return result
                else:
                    print(f"   ❌ {provider}/{model_name}: 字节数据方式 STT转换失败 - {text}")
            except Exception as e4:
                print(f"   ⚠️  字节数据方式失败: {e4}")
            
            # 如果所有方式都失败，记录错误
            result["error"] = "STT转换失败 - 所有输入方式都失败"
            
        except Exception as e:
            result["error"] = f"STT转换异常: {e}"
        finally:
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
    except Exception as e:
        result["error"] = f"验证异常: {e}"
    
    return result


async def validate_stt_models_factory():
    """
    验证STT模型工厂的完整功能
    """
    print("🚀 启动STT模型工厂功能验证...")
    print("=" * 60)
    print("🔍 STT模型工厂功能验证开始")
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
        if hasattr(stt_factory, '_config') and stt_factory._config:
            providers = stt_factory._config.get("models", {})
            print(f"   配置加载: ✅ 通过 - 加载了 {len(providers)} 个提供商配置")
            validation_results["config_loading"] = True
        else:
            print(f"   配置加载: ❌ 失败 - 未加载到任何配置")
    except Exception as e:
        print(f"   配置加载: ❌ 失败 - {e}")
    
    # 2. 支持的模型验证
    print("\n📋 2. 支持的模型验证")
    try:
        supported_models = stt_factory.get_supported_models()
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
        default_provider = stt_factory._config.get("default", {}).get("provider")
        default_model = stt_factory._config.get("default", {}).get("model")
        
        if default_provider and default_model:
            print(f"   默认模型: {default_provider}/{default_model}")
            default_result = await validate_single_stt_model(default_provider, default_model)
            validation_results["model_creation"] = default_result["model_creation"]
        else:
            print("   默认模型: ❌ 未配置")
            default_result = {"error": "未配置默认模型"}
    except Exception as e:
        print(f"   默认模型验证: ❌ 失败 - {e}")
        default_result = {"error": str(e)}
    
    # 3.2 所有有效模型验证
    print("   3.2 所有有效模型验证")
    supported_models = stt_factory.get_supported_models()
    all_models_results = []
    
    for provider, provider_info in supported_models.items():
        models = provider_info.get("models", {})
        for model_name in models.keys():
            print(f"\n   {'='*50}")
            print(f"   验证模型: {provider}/{model_name}")
            print(f"   {'='*50}")
            result = await validate_single_stt_model(provider, model_name)
            all_models_results.append(result)
    
    # 统计结果
    print(f"\n   验证结果统计:")
    print(f"   总模型数: {len(all_models_results)}")
    model_creation_success = sum(1 for r in all_models_results if r["model_creation"])
    stt_success = sum(1 for r in all_models_results if r["stt"])
    print(f"   模型创建成功: {model_creation_success}")
    print(f"   STT转换成功: {stt_success}")
    
    # 默认模型结果
    if default_result["error"]:
        print(f"   默认模型验证: ❌ 失败 - {default_result['error']}")
    else:
        print(f"   默认模型验证: ✅ 通过")
        print(f"   模型创建: {'✅' if default_result['model_creation'] else '❌'}")
        print(f"   STT转换: {'✅' if default_result['stt'] else '❌'}")
    
    # 4. 错误处理验证
    print("\n📋 4. 错误处理验证")
    try:
        print("   测试无效模型创建...")
        try:
            invalid_model = stt_factory.create_model("invalid_provider", "invalid_model")
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
    print("📊 STT模型工厂验证结果汇总")
    print("=" * 60)
    
    for key, value in validation_results.items():
        status = "✅ 通过" if value else "❌ 失败"
        print(f"   {key}: {status}")
    
    passed_tests = sum(validation_results.values())
    total_tests = len(validation_results)
    print(f"\n📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有STT模型功能验证通过！")
    else:
        print("⚠️  部分STT模型功能验证失败，请检查上述错误信息")
    
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
    
    asyncio.run(validate_stt_models_factory())