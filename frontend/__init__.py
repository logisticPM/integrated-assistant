#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
前端模块 - 提供Gradio界面组件
"""

from frontend.main_ui import create_main_interface
from frontend.meeting_ui import create_meeting_interface
from frontend.email_ui import create_email_interface
from frontend.knowledge_ui import create_knowledge_interface

__all__ = [
    "create_main_interface",
    "create_meeting_interface",
    "create_email_interface",
    "create_knowledge_interface"
]
