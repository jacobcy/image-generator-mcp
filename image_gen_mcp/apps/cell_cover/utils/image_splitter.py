from PIL import Image
import os
import shutil

def split_image_into_four(input_path, current_dir=None, selected_parts=None):
    """将一张图片分割成四等份，所有切割照片保存到images文件夹，选中的照片复制到当前目录

    Args:
        input_path (str): 输入图片的路径
        current_dir (str, optional): 当前工作目录，用于保存选中的照片。如果为None，则使用当前工作目录
        selected_parts (list, optional): 要复制到当前目录的部分列表 (u1, u2, u3, u4)

    Returns:
        tuple: (所有输出文件路径列表, 选中文件路径列表)
    """
    # 打开图片
    img = Image.open(input_path)

    # 获取图片尺寸
    width, height = img.size

    # 计算每个部分的尺寸
    part_width = width // 2
    part_height = height // 2

    # 设置当前工作目录，如果没有指定则使用当前工作目录
    if current_dir is None:
        current_dir = os.getcwd()

    # 创建images文件夹用于保存所有切割照片
    images_dir = os.path.join(current_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # 确保当前目录存在（用于保存选中的照片）
    os.makedirs(current_dir, exist_ok=True)

    # 文件名（不含扩展名）和扩展名
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1]

    # 分割坐标
    boxes = [
        (0, 0, part_width, part_height),                    # 左上 u1
        (part_width, 0, width, part_height),                # 右上 u2
        (0, part_height, part_width, height),               # 左下 u3
        (part_width, part_height, width, height)            # 右下 u4
    ]

    # 分割并保存图片
    output_paths = []
    selected_paths = []
    positions = ['u1', 'u2', 'u3', 'u4']

    for i, box in enumerate(boxes):
        # 裁剪图片
        part = img.crop(box)

        # 生成输出文件路径（保存到images文件夹）
        position = positions[i]
        output_path = os.path.join(images_dir, f"{base_name}_{position}{ext}")

        # 保存图片到images文件夹
        part.save(output_path)
        output_paths.append(output_path)

        # 如果这个部分被选中，复制到当前目录
        if selected_parts and position in selected_parts:
            selected_path = os.path.join(current_dir, f"{base_name}_{position}{ext}")
            shutil.copy2(output_path, selected_path)
            selected_paths.append(selected_path)

    return output_paths, selected_paths

def main():
    """主函数，用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description='将图片分割成四等份')
    parser.add_argument('input_path', help='输入图片路径')
    parser.add_argument('--current-dir', help='当前工作目录（可选，默认为当前目录）')
    parser.add_argument('--select', nargs='+', choices=['u1', 'u2', 'u3', 'u4'],
                        help='选择要复制到当前目录的部分（可选，例如：--select u1 u2）')

    args = parser.parse_args()

    try:
        output_paths, selected_paths = split_image_into_four(
            args.input_path,
            args.current_dir,
            args.select
        )

        print("\n图片已成功分割！输出文件：")
        for path in output_paths:
            print(f"- {path}")

        if selected_paths:
            print("\n选中的文件已复制到当前目录：")
            for path in selected_paths:
                print(f"- {path}")

    except Exception as e:
        print(f"处理图片时出错：{e}")

if __name__ == '__main__':
    main()
