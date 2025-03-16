#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮件处理脚本 - 自动获取和处理邮件
参考executive-ai-assistant项目的run_ingest.py
"""

import os
import sys
import argparse
import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from mcp.client import MCPClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_processor")

def load_config():
    """加载配置"""
    config_path = os.path.join(project_root, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return {
            "mcp": {
                "host": "127.0.0.1",
                "port": 5001
            }
        }

def process_emails(
    minutes_since=60,
    email_address=None,
    query=None,
    max_results=50,
    auto_reply=False,
    auto_categorize=True,
    auto_mark_read=False
):
    """
    处理邮件
    
    Args:
        minutes_since: 处理多少分钟前的邮件
        email_address: 邮箱地址
        query: 自定义查询
        max_results: 最大处理数量
        auto_reply: 是否自动回复
        auto_categorize: 是否自动分类
        auto_mark_read: 是否自动标记为已读
    
    Returns:
        处理结果
    """
    try:
        # 加载配置
        config = load_config()
        
        # 创建MCP客户端
        mcp_client = MCPClient(config)
        
        # 测试Gmail连接
        connection_test = mcp_client.call("gmail.test_connection")
        if not connection_test["success"]:
            logger.error(f"Gmail连接失败: {connection_test['message']}")
            return {"success": False, "message": connection_test["message"]}
        
        # 如果未指定邮箱地址，使用连接测试中返回的地址
        if not email_address:
            email_address = connection_test.get("email", "")
            logger.info(f"使用邮箱地址: {email_address}")
        
        # 构建查询
        if not query:
            # 计算时间范围
            after_time = int((datetime.now() - timedelta(minutes=minutes_since)).timestamp())
            query = f"after:{after_time}"
        
        # 获取邮件列表
        logger.info(f"正在获取邮件, 查询: {query}")
        emails = mcp_client.call("gmail.list_emails", {
            "max_results": max_results,
            "query": query,
            "include_body": True
        })
        
        if not emails:
            logger.info("没有找到符合条件的邮件")
            return {"success": True, "message": "没有找到符合条件的邮件", "count": 0}
        
        logger.info(f"找到 {len(emails)} 封邮件")
        
        # 处理每封邮件
        processed_count = 0
        for email in emails:
            try:
                # 提取邮件信息
                email_id = email["id"]
                thread_id = email["thread_id"]
                subject = email["subject"]
                sender = email["sender"]
                
                logger.info(f"处理邮件: {subject} (来自: {sender})")
                
                # 自动标记为已读
                if auto_mark_read:
                    mcp_client.call("gmail.mark_as_read", {"message_id": email_id})
                    logger.info(f"邮件已标记为已读: {email_id}")
                
                # 自动分类
                if auto_categorize:
                    # 调用邮件分析服务
                    analysis = mcp_client.call("email.analyze_email", {
                        "subject": subject,
                        "body": email.get("body", ""),
                        "sender": sender
                    })
                    
                    logger.info(f"邮件分析结果: 类别={analysis.get('category', '未知')}, 优先级={analysis.get('priority', '中')}")
                    
                    # 保存到数据库
                    mcp_client.call("email.save_email", {
                        "email_data": email,
                        "analysis": analysis
                    })
                
                # 自动回复
                if auto_reply:
                    # 检查是否需要自动回复
                    should_reply = mcp_client.call("email.should_auto_reply", {
                        "email_id": email_id,
                        "subject": subject,
                        "sender": sender
                    })
                    
                    if should_reply.get("should_reply", False):
                        # 生成回复内容
                        reply_content = mcp_client.call("email.generate_reply", {
                            "email_id": email_id,
                            "subject": subject,
                            "body": email.get("body", ""),
                            "sender": sender
                        })
                        
                        # 发送回复
                        if reply_content.get("success", False):
                            reply_result = mcp_client.call("gmail.send_email", {
                                "to": sender,
                                "subject": f"Re: {subject}",
                                "body": reply_content.get("reply", ""),
                                "reply_to": email_id
                            })
                            
                            logger.info(f"自动回复已发送: {reply_result.get('message', '')}")
                
                processed_count += 1
            
            except Exception as e:
                logger.error(f"处理邮件失败: {str(e)}")
        
        return {
            "success": True,
            "message": f"成功处理 {processed_count} 封邮件",
            "count": processed_count
        }
    
    except Exception as e:
        logger.exception("邮件处理失败")
        return {"success": False, "message": f"邮件处理失败: {str(e)}"}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="邮件处理脚本")
    
    parser.add_argument(
        "--minutes-since",
        type=int,
        default=60,
        help="处理多少分钟前的邮件"
    )
    
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="指定邮箱地址"
    )
    
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="自定义查询条件"
    )
    
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="最大处理数量"
    )
    
    parser.add_argument(
        "--auto-reply",
        action="store_true",
        help="启用自动回复"
    )
    
    parser.add_argument(
        "--auto-categorize",
        action="store_true",
        help="启用自动分类"
    )
    
    parser.add_argument(
        "--auto-mark-read",
        action="store_true",
        help="启用自动标记为已读"
    )
    
    args = parser.parse_args()
    
    # 处理邮件
    result = process_emails(
        minutes_since=args.minutes_since,
        email_address=args.email,
        query=args.query,
        max_results=args.max_results,
        auto_reply=args.auto_reply,
        auto_categorize=args.auto_categorize,
        auto_mark_read=args.auto_mark_read
    )
    
    # 输出结果
    if result["success"]:
        logger.info(result["message"])
    else:
        logger.error(result["message"])

if __name__ == "__main__":
    main()
