#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮件分析服务 - 提供邮件分类、优先级判断和情感分析功能
"""

import re
import logging
import json
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter, defaultdict
import numpy as np
from io import BytesIO
import base64

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_analysis")

class EmailAnalysisService:
    """邮件分析服务类"""
    
    def __init__(self, config, mcp_server=None):
        """
        初始化邮件分析服务
        
        Args:
            config: 配置信息
            mcp_server: MCP服务器实例
        """
        self.config = config
        self.mcp_server = mcp_server
        
        # 加载分类关键词
        self.category_keywords = {
            "工作": ["项目", "任务", "工作", "会议", "报告", "deadline", "进度", "完成", "提交"],
            "通知": ["通知", "公告", "提醒", "注意", "重要", "attention", "announcement"],
            "营销": ["促销", "折扣", "优惠", "限时", "特价", "sale", "discount", "offer"],
            "社交": ["邀请", "聚会", "活动", "party", "social", "gathering"],
            "账户": ["账户", "密码", "登录", "注册", "验证", "account", "password", "login"],
            "订阅": ["订阅", "newsletter", "更新", "周报", "月报", "update", "subscribe"],
            "其他": []
        }
        
        # 优先级关键词
        self.priority_keywords = {
            "高": ["urgent", "紧急", "重要", "立即", "immediately", "asap", "尽快", "deadline", "今天"],
            "中": ["请关注", "请查看", "请回复", "需要", "重要", "important", "注意", "attention"],
            "低": ["fyi", "参考", "供参考", "newsletter", "订阅", "通讯", "weekly", "monthly"]
        }
        
        # 情感分析关键词
        self.sentiment_keywords = {
            "正面": ["感谢", "谢谢", "好", "棒", "优秀", "满意", "happy", "thanks", "good", "great", "excellent", "appreciate"],
            "负面": ["投诉", "不满", "差", "问题", "错误", "失败", "bad", "poor", "issue", "problem", "error", "fail", "complaint"],
            "中性": []
        }
    
    def analyze_email(self, subject, body, sender, **kwargs):
        """
        分析单封邮件
        
        Args:
            subject: 邮件主题
            body: 邮件正文
            sender: 发件人
            **kwargs: 其他参数
        
        Returns:
            分析结果
        """
        try:
            # 合并主题和正文用于分析
            content = f"{subject} {body}"
            
            # 分类
            category = self._classify_email(subject, content)
            
            # 优先级
            priority = self._determine_priority(subject, content)
            
            # 情感分析
            sentiment = self._analyze_sentiment(content)
            
            # 关键词提取
            keywords = self._extract_keywords(content)
            
            # 是否需要回复
            needs_reply = self._needs_reply(subject, content)
            
            # 是否为自动生成邮件
            is_automated = self._is_automated(sender, content)
            
            # 返回分析结果
            return {
                "category": category,
                "priority": priority,
                "sentiment": sentiment,
                "keywords": keywords,
                "needs_reply": needs_reply,
                "is_automated": is_automated,
                "analysis_time": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.exception(f"邮件分析失败: {str(e)}")
            return {
                "category": "未知",
                "priority": "中",
                "sentiment": "中性",
                "keywords": [],
                "needs_reply": False,
                "is_automated": False,
                "error": str(e)
            }
    
    def analyze_batch(self, emails, **kwargs):
        """
        批量分析邮件
        
        Args:
            emails: 邮件列表
            **kwargs: 其他参数
        
        Returns:
            批量分析结果
        """
        try:
            results = []
            
            # 分析每封邮件
            for email in emails:
                subject = email.get("subject", "")
                body = email.get("body", "")
                sender = email.get("sender", "")
                
                analysis = self.analyze_email(subject, body, sender)
                
                # 添加邮件ID
                analysis["email_id"] = email.get("id", "")
                
                results.append(analysis)
            
            # 生成统计图表
            stats = self._generate_statistics(emails, results)
            
            return {
                "individual_results": results,
                "category_plot": stats["category_plot"],
                "sender_plot": stats["sender_plot"],
                "time_plot": stats["time_plot"],
                "topics": stats["topics"]
            }
        
        except Exception as e:
            logger.exception(f"批量邮件分析失败: {str(e)}")
            return {
                "individual_results": [],
                "error": str(e)
            }
    
    def _classify_email(self, subject, content):
        """
        对邮件进行分类
        
        Args:
            subject: 邮件主题
            content: 邮件内容
        
        Returns:
            分类结果
        """
        # 计算每个类别的匹配分数
        scores = {}
        
        for category, keywords in self.category_keywords.items():
            if not keywords:  # 跳过"其他"类别
                continue
                
            score = 0
            for keyword in keywords:
                # 在主题中出现的关键词权重更高
                if keyword.lower() in subject.lower():
                    score += 2
                
                # 在内容中出现的关键词
                if keyword.lower() in content.lower():
                    score += 1
            
            scores[category] = score
        
        # 如果有明确的分类，返回得分最高的
        if scores and max(scores.values()) > 0:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        # 否则返回"其他"
        return "其他"
    
    def _determine_priority(self, subject, content):
        """
        确定邮件优先级
        
        Args:
            subject: 邮件主题
            content: 邮件内容
        
        Returns:
            优先级
        """
        # 计算每个优先级的匹配分数
        scores = {}
        
        for priority, keywords in self.priority_keywords.items():
            score = 0
            for keyword in keywords:
                # 在主题中出现的关键词权重更高
                if keyword.lower() in subject.lower():
                    score += 2
                
                # 在内容中出现的关键词
                if keyword.lower() in content.lower():
                    score += 1
            
            scores[priority] = score
        
        # 如果有明确的优先级，返回得分最高的
        if scores and max(scores.values()) > 0:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        # 否则返回"中"优先级
        return "中"
    
    def _analyze_sentiment(self, content):
        """
        分析邮件情感
        
        Args:
            content: 邮件内容
        
        Returns:
            情感分析结果
        """
        # 计算每种情感的匹配分数
        scores = {}
        
        for sentiment, keywords in self.sentiment_keywords.items():
            if not keywords:  # 跳过"中性"情感
                continue
                
            score = 0
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    score += 1
            
            scores[sentiment] = score
        
        # 如果有明确的情感，返回得分最高的
        if scores and max(scores.values()) > 0:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        # 否则返回"中性"
        return "中性"
    
    def _extract_keywords(self, content, max_keywords=5):
        """
        提取邮件关键词
        
        Args:
            content: 邮件内容
            max_keywords: 最大关键词数量
        
        Returns:
            关键词列表
        """
        # 简单实现，实际应用中可以使用更复杂的算法
        # 如TF-IDF或TextRank
        
        # 移除常见停用词
        stop_words = ["的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and", "in", "that", "have", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from"]
        
        # 分词并计数
        words = re.findall(r'\b\w+\b', content.lower())
        word_counts = Counter(word for word in words if word not in stop_words and len(word) > 1)
        
        # 返回出现频率最高的几个词
        return [word for word, count in word_counts.most_common(max_keywords)]
    
    def _needs_reply(self, subject, content):
        """
        判断邮件是否需要回复
        
        Args:
            subject: 邮件主题
            content: 邮件内容
        
        Returns:
            是否需要回复
        """
        # 检查是否包含问句
        has_question = "?" in content or "？" in content
        
        # 检查是否包含请求回复的关键词
        reply_keywords = ["请回复", "请回答", "请告知", "请提供", "期待回复", "please reply", "please respond", "looking forward to", "get back to me", "let me know"]
        has_reply_request = any(keyword in content.lower() for keyword in reply_keywords)
        
        # 检查是否是自动发送的通知邮件
        noreply_indicators = ["no-reply", "noreply", "do-not-reply", "donotreply", "自动发送", "automatic", "notification", "system"]
        is_noreply = any(indicator in subject.lower() or indicator in content.lower() for indicator in noreply_indicators)
        
        # 综合判断
        return (has_question or has_reply_request) and not is_noreply
    
    def _is_automated(self, sender, content):
        """
        判断是否为自动生成的邮件
        
        Args:
            sender: 发件人
            content: 邮件内容
        
        Returns:
            是否为自动生成
        """
        # 检查发件人是否包含自动发送的标识
        auto_senders = ["no-reply", "noreply", "do-not-reply", "donotreply", "system", "notification", "alert", "info", "support"]
        sender_is_auto = any(indicator in sender.lower() for indicator in auto_senders)
        
        # 检查内容是否包含自动邮件的特征
        auto_content_indicators = ["自动发送", "请勿回复", "系统通知", "自动通知", "automated", "automatic", "do not reply", "system generated"]
        content_is_auto = any(indicator in content.lower() for indicator in auto_content_indicators)
        
        # 检查是否包含典型的自动邮件格式
        has_auto_format = "this is an automated message" in content.lower() or "这是一封自动生成的邮件" in content.lower()
        
        return sender_is_auto or content_is_auto or has_auto_format
    
    def _generate_statistics(self, emails, analysis_results):
        """
        生成统计数据和图表
        
        Args:
            emails: 邮件列表
            analysis_results: 分析结果列表
        
        Returns:
            统计数据和图表
        """
        # 提取类别统计
        categories = [result["category"] for result in analysis_results]
        category_counts = Counter(categories)
        
        # 提取发件人统计
        senders = [email.get("sender", "").split("<")[0].strip() for email in emails]
        sender_counts = Counter(senders)
        top_senders = dict(sender_counts.most_common(10))
        
        # 提取时间分布
        dates = []
        for email in emails:
            try:
                date_str = email.get("date", "")
                # 尝试解析日期
                if date_str:
                    date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    dates.append(date.strftime("%Y-%m-%d"))
            except Exception:
                continue
        
        date_counts = Counter(dates)
        
        # 生成类别分布图
        category_plot = self._create_pie_chart(category_counts, "邮件类别分布")
        
        # 生成发件人分布图
        sender_plot = self._create_bar_chart(top_senders, "发件人分布")
        
        # 生成时间分布图
        time_plot = self._create_line_chart(date_counts, "邮件时间分布")
        
        # 提取主题
        topics = self._extract_topics(analysis_results)
        
        return {
            "category_plot": category_plot,
            "sender_plot": sender_plot,
            "time_plot": time_plot,
            "topics": topics
        }
    
    def _create_pie_chart(self, data, title):
        """
        创建饼图
        
        Args:
            data: 数据
            title: 标题
        
        Returns:
            Base64编码的图片
        """
        plt.figure(figsize=(8, 6))
        plt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title(title)
        
        # 保存为Base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _create_bar_chart(self, data, title):
        """
        创建柱状图
        
        Args:
            data: 数据
            title: 标题
        
        Returns:
            Base64编码的图片
        """
        plt.figure(figsize=(10, 6))
        plt.bar(data.keys(), data.values())
        plt.xticks(rotation=45, ha='right')
        plt.title(title)
        plt.tight_layout()
        
        # 保存为Base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _create_line_chart(self, data, title):
        """
        创建折线图
        
        Args:
            data: 数据
            title: 标题
        
        Returns:
            Base64编码的图片
        """
        # 排序日期
        sorted_dates = sorted(data.keys())
        values = [data[date] for date in sorted_dates]
        
        plt.figure(figsize=(10, 6))
        plt.plot(sorted_dates, values, marker='o')
        plt.xticks(rotation=45, ha='right')
        plt.title(title)
        plt.tight_layout()
        
        # 保存为Base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _extract_topics(self, analysis_results):
        """
        提取主题
        
        Args:
            analysis_results: 分析结果列表
        
        Returns:
            主题列表
        """
        # 收集所有关键词
        all_keywords = []
        for result in analysis_results:
            all_keywords.extend(result.get("keywords", []))
        
        # 计算关键词频率
        keyword_counts = Counter(all_keywords)
        
        # 提取前10个主题
        topics = []
        for keyword, count in keyword_counts.most_common(10):
            # 确定重要性
            importance = "高" if count > 3 else "中" if count > 1 else "低"
            
            topics.append({
                "name": keyword,
                "count": count,
                "importance": importance
            })
        
        return topics

def register_email_analysis_service(mcp_server):
    """
    注册邮件分析服务
    
    Args:
        mcp_server: MCP服务器实例
    """
    # 创建服务实例
    email_analysis_service = EmailAnalysisService(mcp_server.config, mcp_server)
    
    # 注册分析单封邮件的方法
    @mcp_server.register_method("email.analyze_email")
    def analyze_email(subject, body, sender, **kwargs):
        return email_analysis_service.analyze_email(subject, body, sender, **kwargs)
    
    # 注册批量分析邮件的方法
    @mcp_server.register_method("email.analyze_batch")
    def analyze_batch(emails, **kwargs):
        return email_analysis_service.analyze_batch(emails, **kwargs)
    
    # 注册判断是否需要自动回复的方法
    @mcp_server.register_method("email.should_auto_reply")
    def should_auto_reply(email_id, subject, sender, **kwargs):
        # 获取邮件内容
        email = mcp_server.call_method("gmail.get_email", {"message_id": email_id, "include_body": True})
        
        if not email:
            return {"should_reply": False, "reason": "未找到邮件"}
        
        # 分析邮件
        analysis = email_analysis_service.analyze_email(subject, email.get("body", ""), sender)
        
        # 判断是否需要回复
        should_reply = analysis.get("needs_reply", False) and not analysis.get("is_automated", False)
        
        return {
            "should_reply": should_reply,
            "reason": "需要回复" if should_reply else "不需要回复",
            "analysis": analysis
        }
    
    # 注册生成回复的方法
    @mcp_server.register_method("email.generate_reply")
    def generate_reply(email_id, subject, body, sender, **kwargs):
        try:
            # 分析邮件
            analysis = email_analysis_service.analyze_email(subject, body, sender)
            
            # 使用LLM生成回复
            prompt = f"""
            你是一位专业的邮件助手。请根据以下邮件内容，生成一个合适的回复。
            
            发件人: {sender}
            主题: {subject}
            内容: {body}
            
            邮件分析:
            - 类别: {analysis.get('category', '未知')}
            - 优先级: {analysis.get('priority', '中')}
            - 情感: {analysis.get('sentiment', '中性')}
            - 关键词: {', '.join(analysis.get('keywords', []))}
            
            请直接给出回复内容，不要包含解释。回复应该专业、简洁，并针对邮件内容提供有用的信息或回应。
            """
            
            # 调用LLM服务
            llm_response = mcp_server.call_method("llm.generate", {
                "prompt": prompt,
                "max_tokens": 500
            })
            
            reply_text = llm_response.get("text", "")
            
            return {
                "success": True,
                "reply": reply_text,
                "analysis": analysis
            }
        
        except Exception as e:
            logger.exception(f"生成回复失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # 注册保存邮件的方法
    @mcp_server.register_method("email.save_email")
    def save_email(email_data, analysis, **kwargs):
        try:
            # 在实际应用中，这里应该将邮件和分析结果保存到数据库
            # 这里仅作为示例
            logger.info(f"保存邮件: {email_data.get('id', '')}, 类别: {analysis.get('category', '未知')}")
            
            return {
                "success": True,
                "message": "邮件已保存"
            }
        
        except Exception as e:
            logger.exception(f"保存邮件失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # 注册语义搜索方法
    @mcp_server.register_method("email.semantic_search")
    def semantic_search(query, max_results=10, **kwargs):
        try:
            # 获取所有邮件
            emails = mcp_server.call_method("gmail.list_emails", {
                "max_results": 100,
                "include_body": True
            })
            
            if not emails:
                return []
            
            # 使用向量服务进行语义搜索
            # 实际应用中应该使用向量数据库或嵌入模型
            # 这里使用简单的关键词匹配作为示例
            results = []
            
            for email in emails:
                # 计算相关度（简化版）
                relevance = 0
                
                # 检查主题
                if query.lower() in email.get("subject", "").lower():
                    relevance += 0.5
                
                # 检查正文
                if query.lower() in email.get("body", "").lower():
                    relevance += 0.3
                
                # 检查发件人
                if query.lower() in email.get("sender", "").lower():
                    relevance += 0.2
                
                # 如果有相关性，添加到结果
                if relevance > 0:
                    results.append({
                        "id": email.get("id", ""),
                        "sender": email.get("sender", ""),
                        "subject": email.get("subject", ""),
                        "date": email.get("date", ""),
                        "relevance": relevance
                    })
            
            # 按相关度排序
            results.sort(key=lambda x: x["relevance"], reverse=True)
            
            # 返回前N个结果
            return results[:max_results]
        
        except Exception as e:
            logger.exception(f"语义搜索失败: {str(e)}")
            return []
    
    logger.info("邮件分析服务已注册")
