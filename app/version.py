# -*- coding: utf-8 -*-
"""版本与作者信息。

开源仓库地址在这里修改（应用内不提供修改入口）：
    本文件中 GITHUB 常量。
修改后重启程序生效。
"""

APP_VERSION = "2.6.0"
AUTHOR = "hbhbhbhbhvb"
GITHUB = ""   # 开源后填你的仓库地址，如 "https://github.com/hbhbhbhbhvb/sport-meet"
DESCRIPTION = "学校运动会秩序册自动生成工具（报名表导入 -> 智能识别 -> 冲突检查 -> Word 秩序册）"


def get_about():
    return {
        "version": APP_VERSION,
        "author": AUTHOR,
        "github": GITHUB,
        "description": DESCRIPTION,
    }
