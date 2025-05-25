#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def handle_list_styles(config):
    """处理 'list-styles' 命令，列出所有可用的全局样式。"""
    global_styles = config.get("global_styles", {})
    
    if not global_styles:
        print("未找到可用的样式选项。")
        return 1
    
    print("可用的全局样式选项:")
    print("=" * 50)
    
    # 按字母顺序排序样式
    sorted_styles = sorted(global_styles.items())
    
    for style_key, style_description in sorted_styles:
        print(f"\n🎨 {style_key}")
        print(f"   {style_description}")
    
    print("\n" + "=" * 50)
    print(f"总共 {len(global_styles)} 个可用样式")
    print("\n使用方法:")
    print("  crc generate --style <style_name> [其他选项]")
    print("  crc create --style <style_name> [其他选项]")
    print("\n示例:")
    print("  crc generate --concept ca --style cinematic")
    print("  crc create --concept ca --style focus,vibrant_colors")
    
    return 0
