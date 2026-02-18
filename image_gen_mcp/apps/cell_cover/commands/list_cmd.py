# -*- coding: utf-8 -*-

def handle_list_concepts(config):
    """处理 'list-concepts' 命令，列出所有可用的创意概念。"""
    print("可用的创意概念:")
    concepts = config.get("concepts", {})
    if not concepts:
        print("警告：配置文件中没有找到任何概念")
        print("  配置文件中没有找到任何概念。")
        return 0 # Indicate success (no concepts found is not an error here)

    for key, concept in concepts.items():
        print(f"  - {key}: {concept.get('name', 'N/A')}")
        print(f"    {concept.get('description', '无描述')}")
        print()
    return 0

def handle_list_variations(config, concept_key: str):
    """处理 'variations' 命令，列出指定概念的所有变体。"""
    concepts = config.get("concepts", {})
    if concept_key not in concepts:
        print(f"错误：找不到创意概念 '{concept_key}'")
        return 1 # Indicate error

    concept = concepts[concept_key]
    variations = concept.get("variations", {})
    print(f"'{concept.get('name', concept_key)}'的可用变体:")
    if not variations:
        print(f"警告：概念 '{concept_key}' 没有定义变体")
        print("  此概念没有定义变体。")
        return 0 # Indicate success (no variations found is not an error)

    for key, desc in variations.items():
        print(f"  - {key}: {desc}")
    print()
    return 0
