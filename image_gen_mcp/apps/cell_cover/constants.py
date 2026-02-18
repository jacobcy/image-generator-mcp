# -*- coding: utf-8 -*-

"""
存储项目共享的常量。
"""

# Define available actions and their descriptions globally
ACTION_CHOICES = [
    "variation1", "variation2", "variation3", "variation4",
    "upsample1", "upsample2", "upsample3", "upsample4",
    "reroll", "zoom_out_1.5", "zoom_out_2",
    "pan_up", "pan_down", "pan_left", "pan_right"
]

ACTION_DESCRIPTIONS = {
    "variation1": "创建变体 1",
    "variation2": "创建变体 2",
    "variation3": "创建变体 3",
    "variation4": "创建变体 4",
    "upsample1": "放大图像 1",
    "upsample2": "放大图像 2",
    "upsample3": "放大图像 3",
    "upsample4": "放大图像 4",
    "reroll": "重新生成任务",
    "zoom_out_1.5": "缩小 1.5 倍",
    "zoom_out_2": "缩小 2 倍",
    "pan_up": "向上平移图像",
    "pan_down": "向下平移图像",
    "pan_left": "向左平移图像",
    "pan_right": "向右平移图像",
    # Add more descriptions as needed
} 