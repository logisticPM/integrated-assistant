#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
知识库界面模块 - 提供文档上传、搜索和查询功能
"""

import gradio as gr
import os

class KnowledgeInterface:
    """知识库界面类"""
    
    def __init__(self, mcp_client, config):
        """
        初始化知识库界面
        
        Args:
            mcp_client: MCP客户端实例
            config: 应用配置
        """
        self.mcp_client = mcp_client
        self.config = config
        self.docs_dir = config["knowledge"]["docs_dir"]
    
    def render(self):
        """渲染知识库界面"""
        with gr.Blocks() as interface:
            gr.Markdown("## 知识库管理")
            
            with gr.Tabs() as tabs:
                with gr.TabItem("文档上传"):
                    self._create_upload_interface()
                
                with gr.TabItem("知识库搜索"):
                    self._create_search_interface()
                
                with gr.TabItem("文档列表"):
                    self._create_document_list_interface()
                
                with gr.TabItem("知识库聊天"):
                    self._create_chat_interface()
            
            return interface
    
    def _create_upload_interface(self):
        """创建文档上传界面"""
        with gr.Group():
            gr.Markdown("### 上传文档")
            
            with gr.Row():
                with gr.Column(scale=2):
                    document_title = gr.Textbox(label="文档标题", placeholder="请输入文档标题")
                    document_category = gr.Dropdown(
                        choices=["会议记录", "技术文档", "产品规格", "市场分析", "其他"],
                        label="文档类别"
                    )
                    document_tags = gr.Textbox(
                        label="标签", 
                        placeholder="输入标签，用逗号分隔"
                    )
                
                with gr.Column(scale=3):
                    document_file = gr.File(label="文档文件")
                    
                    with gr.Row():
                        upload_btn = gr.Button("上传并处理")
                        clear_btn = gr.Button("清除")
            
            upload_status = gr.Textbox(label="上传状态", interactive=False)
            
            # 上传并处理文档
            def upload_and_process(title, category, tags, file_path):
                if not title or not file_path:
                    return "请提供文档标题和文件"
                
                try:
                    # 处理标签
                    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                    
                    # 创建文档记录
                    document_id = self.mcp_client.call("knowledge.create_document", {
                        "title": title,
                        "category": category,
                        "tags": tag_list,
                        "file_path": file_path
                    })
                    
                    # 开始处理任务
                    self.mcp_client.call("knowledge.process_document", {
                        "document_id": document_id
                    })
                    
                    return f"文档 '{title}' 已上传，处理任务已启动。文档ID: {document_id}"
                except Exception as e:
                    return f"上传失败: {str(e)}"
            
            # 清除表单
            def clear_form():
                return ["", None, "", None, ""]
            
            # 绑定事件
            upload_btn.click(
                fn=upload_and_process,
                inputs=[document_title, document_category, document_tags, document_file],
                outputs=upload_status
            )
            
            clear_btn.click(
                fn=clear_form,
                outputs=[document_title, document_category, document_tags, document_file, upload_status]
            )
    
    def _create_search_interface(self):
        """创建知识库搜索界面"""
        with gr.Group():
            gr.Markdown("### 知识库搜索")
            
            with gr.Row():
                search_input = gr.Textbox(
                    label="搜索查询",
                    placeholder="输入关键词或问题"
                )
                search_btn = gr.Button("搜索")
            
            with gr.Row():
                with gr.Column(scale=1):
                    filter_category = gr.Dropdown(
                        choices=["全部", "会议记录", "技术文档", "产品规格", "市场分析", "其他"],
                        value="全部",
                        label="按类别筛选"
                    )
                
                with gr.Column(scale=2):
                    filter_tags = gr.Textbox(
                        label="按标签筛选",
                        placeholder="输入标签，用逗号分隔"
                    )
            
            search_results = gr.Dataframe(
                headers=["文档ID", "标题", "类别", "相关段落", "相关度"],
                datatype=["str", "str", "str", "str", "number"],
                label="搜索结果"
            )
            
            with gr.Accordion("搜索结果详情", open=False):
                selected_result_id = gr.Textbox(label="选中的结果ID", interactive=False)
                result_content = gr.Textbox(
                    label="内容",
                    lines=10,
                    interactive=False
                )
            
            # 搜索知识库
            def search_knowledge(query, category, tags):
                if not query:
                    return []
                
                try:
                    # 处理标签
                    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                    
                    # 调用知识库搜索API
                    search_results = self.mcp_client.call("knowledge.search", {
                        "query": query,
                        "category": category if category != "全部" else None,
                        "tags": tag_list
                    })
                    
                    # 格式化搜索结果
                    formatted_results = []
                    for result in search_results:
                        formatted_results.append([
                            result["document_id"],
                            result["title"],
                            result["category"],
                            result["snippet"],
                            result["relevance"]
                        ])
                    
                    return formatted_results
                except Exception as e:
                    return []
            
            # 获取搜索结果详情
            def get_result_details(result_id):
                if not result_id:
                    return ""
                
                try:
                    # 调用获取详情API
                    result_details = self.mcp_client.call("knowledge.get_chunk", {
                        "chunk_id": result_id
                    })
                    
                    return result_details.get("content", "")
                except Exception as e:
                    return f"获取详情失败: {str(e)}"
            
            # 绑定事件
            search_btn.click(
                fn=search_knowledge,
                inputs=[search_input, filter_category, filter_tags],
                outputs=search_results
            )
            
            # 选择搜索结果行时的事件
            def select_result(evt: gr.SelectData, results):
                if results and evt.index[0] < len(results):
                    result_id = results[evt.index[0]][0]
                    return result_id
                return ""
            
            search_results.select(
                fn=select_result,
                inputs=search_results,
                outputs=selected_result_id
            )
            
            selected_result_id.change(
                fn=get_result_details,
                inputs=selected_result_id,
                outputs=result_content
            )
    
    def _create_document_list_interface(self):
        """创建文档列表界面"""
        with gr.Group():
            gr.Markdown("### 文档列表")
            
            with gr.Row():
                refresh_btn = gr.Button("刷新列表")
                filter_dropdown = gr.Dropdown(
                    choices=["全部", "会议记录", "技术文档", "产品规格", "市场分析", "其他"],
                    value="全部",
                    label="按类别筛选"
                )
            
            documents_table = gr.Dataframe(
                headers=["ID", "标题", "类别", "标签", "状态", "创建日期"],
                datatype=["str", "str", "str", "str", "str", "str"],
                label="文档列表"
            )
            
            with gr.Row():
                document_id_input = gr.Textbox(label="文档ID", placeholder="输入文档ID查看详情")
                view_btn = gr.Button("查看详情")
                delete_btn = gr.Button("删除文档")
            
            document_details = gr.JSON(label="文档详情")
            
            # 获取文档列表
            def get_documents(category="全部"):
                try:
                    documents = self.mcp_client.call("knowledge.list_documents", {
                        "category": category if category != "全部" else None
                    })
                    
                    # 格式化文档列表数据
                    formatted_documents = []
                    for doc in documents:
                        formatted_documents.append([
                            doc["id"],
                            doc["title"],
                            doc["category"],
                            ", ".join(doc["tags"]),
                            doc["status"],
                            doc["created_at"]
                        ])
                    
                    return formatted_documents
                except Exception as e:
                    return []
            
            # 获取文档详情
            def get_document_details(document_id):
                if not document_id:
                    return {}
                
                try:
                    # 调用获取文档详情API
                    document_details = self.mcp_client.call("knowledge.get_document", {
                        "document_id": document_id
                    })
                    
                    return document_details
                except Exception as e:
                    return {"error": str(e)}
            
            # 删除文档
            def delete_document(document_id):
                if not document_id:
                    return {}
                
                try:
                    # 调用删除文档API
                    result = self.mcp_client.call("knowledge.delete_document", {
                        "document_id": document_id
                    })
                    
                    # 刷新文档列表
                    documents = get_documents("全部")
                    
                    return {}, documents
                except Exception as e:
                    return {"error": str(e)}, []
            
            # 绑定事件
            refresh_btn.click(
                fn=get_documents,
                inputs=filter_dropdown,
                outputs=documents_table
            )
            
            filter_dropdown.change(
                fn=get_documents,
                inputs=filter_dropdown,
                outputs=documents_table
            )
            
            view_btn.click(
                fn=get_document_details,
                inputs=document_id_input,
                outputs=document_details
            )
            
            delete_btn.click(
                fn=delete_document,
                inputs=document_id_input,
                outputs=[document_details, documents_table]
            )
    
    def _create_chat_interface(self):
        """创建知识库聊天界面"""
        with gr.Group():
            gr.Markdown("### 知识库聊天")
            
            chatbot = gr.Chatbot(height=400, label="聊天")
            
            with gr.Row():
                with gr.Column(scale=4):
                    msg = gr.Textbox(
                        label="输入消息",
                        placeholder="输入您的问题...",
                        lines=2
                    )
                
                with gr.Column(scale=1):
                    send_btn = gr.Button("发送")
            
            with gr.Accordion("聊天设置", open=False):
                with gr.Row():
                    with gr.Column(scale=1):
                        temperature = gr.Slider(
                            minimum=0.1,
                            maximum=1.0,
                            value=0.7,
                            step=0.1,
                            label="Temperature"
                        )
                    
                    with gr.Column(scale=1):
                        filter_category = gr.Dropdown(
                            choices=["全部", "会议记录", "技术文档", "产品规格", "市场分析", "其他"],
                            value="全部",
                            label="限制知识库类别"
                        )
                
                clear_btn = gr.Button("清除对话")
            
            # 知识库聊天
            def knowledge_chat(message, history, temperature, category):
                if not message:
                    return history
                
                try:
                    # 调用知识库聊天API
                    response = self.mcp_client.call("knowledge.chat", {
                        "message": message,
                        "history": history,
                        "temperature": temperature,
                        "category": category if category != "全部" else None
                    })
                    
                    # 更新聊天历史
                    history.append((message, response))
                    return history
                except Exception as e:
                    history.append((message, f"错误: {str(e)}"))
                    return history
            
            # 清除聊天历史
            def clear_chat_history():
                return []
            
            # 绑定事件
            send_btn.click(
                fn=knowledge_chat,
                inputs=[msg, chatbot, temperature, filter_category],
                outputs=chatbot
            ).then(
                fn=lambda: "",
                outputs=msg
            )
            
            msg.submit(
                fn=knowledge_chat,
                inputs=[msg, chatbot, temperature, filter_category],
                outputs=chatbot
            ).then(
                fn=lambda: "",
                outputs=msg
            )
            
            clear_btn.click(
                fn=clear_chat_history,
                outputs=chatbot
            )

def create_knowledge_interface(mcp_client, config):
    """
    创建知识库界面
    
    Args:
        mcp_client: MCP客户端实例
        config: 应用配置
    
    Returns:
        知识库界面实例
    """
    return KnowledgeInterface(mcp_client, config)
