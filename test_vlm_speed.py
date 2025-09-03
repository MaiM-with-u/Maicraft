#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLM响应速度测试脚本
测试多个不同VLM的响应时间和性能
"""

import asyncio
import time
import json
import statistics
from datetime import datetime
from typing import Dict, Any
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from openai_client.modelconfig import ModelConfig
from openai_client.llm_request import LLMClient
from vlm_test_config import VLM_CONFIGS, TEST_IMAGES, TEST_PROMPTS, TEST_PARAMS


class VLMSpeedTester:
    """VLM响应速度测试器"""
    
    def __init__(self):
        self.results = {}
        self.log_file = f"vlm_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    async def test_single_vlm(
        self, 
        vlm_name: str, 
        config: Dict[str, Any], 
        image_url: str, 
        prompt: str
    ) -> Dict[str, Any]:
        """测试单个VLM的响应速度"""
        
        try:
            # 创建模型配置
            model_config = ModelConfig(
                model_name=config["model_name"],
                api_key=config["api_key"],
                base_url=config["base_url"],
                max_tokens=config["max_tokens"],
                temperature=config["temperature"]
            )
            
            # 创建LLM客户端
            client = LLMClient(model_config)
            
            # 记录开始时间
            start_time = time.time()
            
            # 发送VLM请求
            response = await client.vision_completion(
                prompt=prompt,
                images=image_url,
                system_message="你是一个专业的图像分析助手，请用中文回答。"
            )
            
            # 记录结束时间
            end_time = time.time()
            
            # 计算响应时间
            response_time = end_time - start_time
            
            result = {
                "vlm_name": vlm_name,
                "model_name": config["model_name"],
                "prompt": prompt,
                "image_url": image_url,
                "response_time": response_time,
                "success": response.get("success", False),
                "content_length": len(response.get("content", "")) if response.get("content") else 0,
                "token_usage": response.get("usage", {}),
                "error": response.get("error") if not response.get("success") else None,
                "timestamp": datetime.now().isoformat(),
                # 添加模型回复内容记录
                "model_response": response.get("content", "") if response.get("success") else None,
                "model_name_used": response.get("model", config["model_name"]) if response.get("success") else None,
                "finish_reason": response.get("finish_reason", None) if response.get("success") else None,
                # 添加推理链记录
                "reasoning_content": response.get("reasoning_content", None) if response.get("success") else None
            }
            
            return result
            
        except Exception as e:
            return {
                "vlm_name": vlm_name,
                "model_name": config.get("model_name", "unknown"),
                "prompt": prompt,
                "image_url": image_url,
                "response_time": None,
                "success": False,
                "content_length": 0,
                "token_usage": {},
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                # 添加模型回复内容记录（失败时为None）
                "model_response": None,
                "model_name_used": None,
                "finish_reason": None,
                # 添加推理链记录（失败时为None）
                "reasoning_content": None
            }
    
    async def test_vlm_multiple_runs(
        self, 
        vlm_name: str, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """对单个VLM进行多次测试"""
        
        print(f"\n开始测试 {vlm_name} ({config['model_name']})...")
        
        all_results = []
        successful_runs = 0
        
        for run in range(TEST_PARAMS["num_runs"]):
            print(f"  第 {run + 1} 次测试...")
            
            # 随机选择图片和提示词
            import random
            image_url = random.choice(TEST_IMAGES)
            prompt = random.choice(TEST_PROMPTS)
            
            # 执行测试（不打印详细参数）
            result = await self.test_single_vlm(vlm_name, config, image_url, prompt)
            all_results.append(result)
            
            if result["success"]:
                successful_runs += 1
                # 显示模型回复的摘要信息
                response_content = result.get("model_response", "")
                if response_content:
                    # 截取前100个字符作为摘要
                    summary = response_content[:100] + "..." if len(response_content) > 100 else response_content
                    print(f"    ✓ 成功 - 响应时间: {result['response_time']:.2f}秒")
                    print(f"      回复摘要: {summary}")
                else:
                    print(f"    ✓ 成功 - 响应时间: {result['response_time']:.2f}秒")
            else:
                print(f"    ✗ 失败 - 错误: {result['error']}")
            
            # 测试间隔
            if run < TEST_PARAMS["num_runs"] - 1:
                await asyncio.sleep(TEST_PARAMS["delay_between_tests"])
        
        # 计算统计数据
        successful_times = [r["response_time"] for r in all_results if r["success"] and r["response_time"] is not None]
        
        stats = {
            "vlm_name": vlm_name,
            "model_name": config["model_name"],
            "total_runs": TEST_PARAMS["num_runs"],
            "successful_runs": successful_runs,
            "success_rate": successful_runs / TEST_PARAMS["num_runs"] if TEST_PARAMS["num_runs"] > 0 else 0,
            "response_times": successful_times,
            "avg_response_time": statistics.mean(successful_times) if successful_times else None,
            "min_response_time": min(successful_times) if successful_times else None,
            "max_response_time": max(successful_times) if successful_times else None,
            "std_response_time": statistics.stdev(successful_times) if len(successful_times) > 1 else None,
            "all_results": all_results
        }
        
        return stats
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有VLM测试"""
        
        print("🚀 开始VLM响应速度测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试配置: {TEST_PARAMS['num_runs']} 次运行")
        print("=" * 60)
        
        all_stats = {}
        
        # 逐个测试每个VLM
        for vlm_name, config in VLM_CONFIGS.items():
            try:
                stats = await self.test_vlm_multiple_runs(vlm_name, config)
                all_stats[vlm_name] = stats
                
                # 打印统计信息
                if stats["successful_runs"] > 0:
                    print(f"  📊 {vlm_name} 统计:")
                    print(f"    成功率: {stats['success_rate']:.1%}")
                    print(f"    平均响应时间: {stats['avg_response_time']:.2f}秒")
                    print(f"    最快响应: {stats['min_response_time']:.2f}秒")
                    print(f"    最慢响应: {stats['max_response_time']:.2f}秒")
                else:
                    print(f"  ❌ {vlm_name} 所有测试都失败了")
                
            except Exception as e:
                print(f"  💥 测试 {vlm_name} 时发生错误: {str(e)}")
                all_stats[vlm_name] = {
                    "vlm_name": vlm_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # 保存结果
        self.save_results(all_stats)
        
        # 生成报告
        self.generate_report(all_stats)
        
        return all_stats
    
    def save_results(self, results: Dict[str, Any]):
        """保存测试结果到JSON文件"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 测试结果已保存到: {self.log_file}")
        except Exception as e:
            print(f"❌ 保存结果失败: {str(e)}")
    
    def generate_report(self, results: Dict[str, Any]):
        """生成测试报告"""
        
        print("\n" + "=" * 60)
        print("📋 VLM响应速度测试报告")
        print("=" * 60)
        
        # 过滤出成功的测试结果
        successful_tests = {
            name: stats for name, stats in results.items() 
            if isinstance(stats, dict) and stats.get("successful_runs", 0) > 0
        }
        
        if not successful_tests:
            print("❌ 没有成功的测试结果")
            return
        
        # 按平均响应时间排序
        sorted_tests = sorted(
            successful_tests.items(),
            key=lambda x: x[1].get("avg_response_time", float('inf'))
        )
        
        print("\n🏆 性能排名 (按平均响应时间排序):")
        print("-" * 60)
        
        for rank, (vlm_name, stats) in enumerate(sorted_tests, 1):
            avg_time = stats.get("avg_response_time", 0)
            success_rate = stats.get("success_rate", 0)
            model_name = stats.get("model_name", "unknown")
            
            print(f"{rank:2d}. {vlm_name:20s} | {avg_time:6.2f}秒 | 成功率: {success_rate:5.1%} | {model_name}")
        
        # 总体统计
        all_times = []
        total_successful = 0
        total_runs = 0
        
        for stats in successful_tests.values():
            times = stats.get("response_times", [])
            all_times.extend(times)
            total_successful += stats.get("successful_runs", 0)
            total_runs += stats.get("total_runs", 0)
        
        if all_times:
            print("\n📊 总体统计:")
            print(f"   总测试次数: {total_runs}")
            print(f"   成功次数: {total_successful}")
            print(f"   总体成功率: {total_successful/total_runs:.1%}")
            print(f"   最快响应: {min(all_times):.2f}秒")
            print(f"   最慢响应: {max(all_times):.2f}秒")
            print(f"   平均响应: {statistics.mean(all_times):.2f}秒")
        
        # 添加模型回复内容统计
        print("\n💬 模型回复内容统计:")
        print("-" * 60)
        
        for vlm_name, stats in successful_tests.items():
            all_results = stats.get("all_results", [])
            successful_results = [r for r in all_results if r.get("success")]
            
            if successful_results:
                # 计算平均回复长度
                response_lengths = [len(r.get("model_response", "")) for r in successful_results if r.get("model_response")]
                avg_length = statistics.mean(response_lengths) if response_lengths else 0
                
                # 统计回复完成原因
                finish_reasons = {}
                for r in successful_results:
                    reason = r.get("finish_reason", "unknown")
                    finish_reasons[reason] = finish_reasons.get(reason, 0) + 1
                
                print(f"  {vlm_name}:")
                print(f"    平均回复长度: {avg_length:.0f} 字符")
                print(f"    回复完成原因: {finish_reasons}")
                
                # 添加推理链统计
                reasoning_results = [r for r in successful_results if r.get("reasoning_content")]
                if reasoning_results:
                    print(f"    推理链可用: 是 ({len(reasoning_results)}/{len(successful_results)})")
                    # 计算平均推理链长度
                    reasoning_lengths = [len(r.get("reasoning_content", "")) for r in reasoning_results if r.get("reasoning_content")]
                    if reasoning_lengths:
                        avg_reasoning_length = statistics.mean(reasoning_lengths)
                        print(f"    平均推理链长度: {avg_reasoning_length:.0f} 字符")
                else:
                    print("    推理链可用: 否")
        
        print(f"\n📁 详细结果已保存到: {self.log_file}")
        
        # 完整输出不同模型的回答内容
        print("\n🔍 完整模型回答内容对比:")
        print("=" * 80)
        
        for vlm_name, stats in successful_tests.items():
            all_results = stats.get("all_results", [])
            successful_results = [r for r in all_results if r.get("success")]
            
            if successful_results:
                print(f"\n📝 {vlm_name} ({stats.get('model_name', 'unknown')}) 完整回答:")
                print("-" * 60)
                
                for i, result in enumerate(successful_results, 1):
                    prompt = result.get("prompt", "")
                    response = result.get("model_response", "")
                    reasoning = result.get("reasoning_content", "")
                    response_time = result.get("response_time", 0)
                    
                    print(f"\n第 {i} 次测试:")
                    print(f"提示词: {prompt}")
                    print(f"响应时间: {response_time:.2f}秒")
                    
                    # 显示推理链（如果有的话）
                    if reasoning:
                        print("推理链:")
                        print(f"{reasoning}")
                        print("最终回答:")
                    else:
                        print("回答内容:")
                    
                    print(f"{response}")
                    print("-" * 40)


async def main():
    """主函数"""
    
    # 检查配置文件中的API密钥
    print("🔍 检查配置文件...")
    missing_keys = []
    
    for vlm_name, config in VLM_CONFIGS.items():
        if config["api_key"].startswith("your_") or config["api_key"] == "":
            missing_keys.append(vlm_name)
    
    if missing_keys:
        print("⚠️  以下VLM缺少有效的API密钥:")
        for name in missing_keys:
            print(f"   - {name}")
        print("\n请在 vlm_test_config.py 中配置有效的API密钥后再运行测试。")
        return
    
    # 创建测试器并运行测试
    tester = VLMSpeedTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
