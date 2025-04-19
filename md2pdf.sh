#!/bin/zsh

# md2pdf.sh - 将Markdown文件转换为PDF
# 使用方法: ./md2pdf.sh input.md [bibliography.bib]

# 检查是否提供了输入文件
if [ $# -lt 1 ]; then
    echo "使用方法: $0 input.md [bibliography.bib]"
    echo "如果不提供bibliography.bib，脚本将尝试在同一目录下查找references.bib文件"
    exit 1
fi

# 获取输入文件路径和名称
input_file="$1"
input_dir=$(dirname "$input_file")
input_name=$(basename "$input_file" .md)
output_file="${input_dir}/${input_name}.pdf"

# 检查输入文件是否存在
if [ ! -f "$input_file" ]; then
    echo "错误: 找不到输入文件 '$input_file'"
    exit 1
fi

# 确定参考文献文件
if [ $# -ge 2 ]; then
    bib_file="$2"
    if [ ! -f "$bib_file" ]; then
        echo "错误: 找不到参考文献文件 '$bib_file'"
        exit 1
    else
        echo "使用参考文献文件: $bib_file"
        bib_option="--bibliography=$bib_file --citeproc"
    fi
else
    # 尝试在同一目录下查找references.bib文件
    bib_file="${input_dir}/references.bib"
    if [ ! -f "$bib_file" ]; then
        echo "警告: 找不到参考文献文件 '$bib_file'，将不使用参考文献"
        bib_option=""
    else
        echo "使用参考文献文件: $bib_file"
        bib_option="--bibliography=$bib_file --citeproc"
    fi
fi

# 检查CSL文件
csl_file="chicago-author-date.csl"
if [ ! -f "$csl_file" ]; then
    echo "警告: 找不到引用样式文件 '$csl_file'，尝试下载..."
    curl -o "$csl_file" https://raw.githubusercontent.com/citation-style-language/styles/master/chicago-author-date.csl
    if [ ! -f "$csl_file" ]; then
        echo "警告: 下载引用样式失败，将使用默认样式"
        csl_option=""
    else
        echo "已下载引用样式: $csl_file"
        csl_option="--csl=$csl_file"
    fi
else
    echo "使用引用样式文件: $csl_file"
    csl_option="--csl=$csl_file"
fi

# 检查是否安装了pandoc
if ! command -v pandoc &> /dev/null; then
    echo "错误: 未安装pandoc，请先安装pandoc"
    echo "可以使用以下命令安装: brew install pandoc"
    exit 1
fi

# 检查是否安装了xelatex
if ! command -v xelatex &> /dev/null; then
    echo "错误: 未安装xelatex，请先安装MacTeX或BasicTeX"
    echo "可以使用以下命令安装: brew install --cask basictex"
    exit 1
fi

# 检查是否安装了必要的LaTeX包
if ! kpsewhich xeCJK.sty &> /dev/null; then
    echo "警告: 未安装xeCJK包，尝试安装..."
    sudo tlmgr update --self
    sudo tlmgr install xecjk fontspec zhnumber hyperref url xcolor
fi

echo "开始转换 $input_file 为 $output_file ..."

# 处理临时文件
temp_md_file=$(mktemp)
cp "$input_file" "$temp_md_file"

# 创建一个临时的LaTeX头文件，用于强制启用彩色链接
temp_header_file=$(mktemp)
cat > "$temp_header_file" << EOF
\usepackage{xeCJK}
\usepackage{zhnumber}
\usepackage{xcolor}
\usepackage[colorlinks=true,
            linkcolor=blue,
            filecolor=blue,
            urlcolor=blue,
            citecolor=blue,
            breaklinks=true]{hyperref}
\hypersetup{
  pdftitle={\${title}},
  pdfauthor={\${author}},
  pdfborder={0 0 0},
}
EOF

# 检查YAML元数据
if ! grep -q "^---" "$temp_md_file"; then
    echo "未检测到YAML元数据，添加基本元数据..."
    # 创建一个临时文件存储YAML和原文件内容
    temp_yaml_file=$(mktemp)
    
    # 提取文件的第一行作为可能的标题
    first_line=$(head -n 1 "$temp_md_file")
    if [[ $first_line == \#* ]]; then
        # 如果第一行是标题，则去掉#号和空格作为title
        title=$(echo "$first_line" | sed 's/^#\+[[:space:]]*//')
    else
        # 否则使用文件名作为标题
        title="$input_name"
    fi
    
    # 写入YAML元数据
    cat > "$temp_yaml_file" << EOF
---
title: "$title"
author: "作者"
date: "$(date '+%Y年%m月%d日')"
bibliography: references.bib
csl: chicago-author-date.csl
CJKmainfont: "Songti SC"
CJKoptions: BoldFont=STHeiti,ItalicFont=STKaiti
---

EOF
    
    # 将原文件内容添加到YAML后
    cat "$temp_md_file" >> "$temp_yaml_file"
    mv "$temp_yaml_file" "$temp_md_file"
else
    echo "检测到YAML元数据，确保中文支持配置..."
    
    # 检查YAML中是否包含CJK支持
    if ! grep -q "CJKmainfont\|xeCJK" "$temp_md_file"; then
        echo "添加中文支持配置到YAML元数据..."
        
        # 创建临时文件进行修改
        temp_yaml_file=$(mktemp)
        
        # 将YAML结束标记(第二个---)替换为CJK配置和结束标记
        awk '
        BEGIN {yaml_found=0; yaml_end=0}
        /^---/ {
            if (yaml_found==0) {
                yaml_found=1;
                print $0;
                next;
            } else {
                yaml_end=1;
                print "CJKmainfont: "Songti SC"";
                print "CJKoptions: BoldFont=STHeiti,ItalicFont=STKaiti";
                print $0;
                next;
            }
        }
        {print}
        ' "$temp_md_file" > "$temp_yaml_file"
        
        mv "$temp_yaml_file" "$temp_md_file"
    fi
fi

# 确保Markdown文件末尾有参考文献部分
if ! grep -q "# 参考文献" "$temp_md_file" && ! grep -q "# References" "$temp_md_file" && [ -n "$bib_option" ]; then
    echo -e "\n\n# 参考文献\n\n::: {#refs}\n:::\n" >> "$temp_md_file"
fi

# 执行pandoc命令
pandoc_cmd="pandoc "$temp_md_file" -o "$output_file" \
    --from=markdown+tex_math_single_backslash+citations+smart \
    --to=pdf \
    --pdf-engine=xelatex \
    --standalone \
    --toc \
    --include-in-header="$temp_header_file" \
    --metadata=link-citations:true \
    --metadata=link-bibliography:true \
    --metadata=documentclass:article \
    --variable=colorlinks:true \
    --variable=linkcolor:blue \
    --variable=urlcolor:blue \
    --variable=citecolor:blue"

# 添加参考文献选项（如果有）
if [ -n "$bib_option" ]; then
    pandoc_cmd="$pandoc_cmd $bib_option"
fi

# 添加引用样式选项（如果有）
if [ -n "$csl_option" ]; then
    pandoc_cmd="$pandoc_cmd $csl_option"
fi

# 执行命令
eval $pandoc_cmd

# 删除临时文件
rm "$temp_md_file" "$temp_header_file"

# 检查转换是否成功
if [ $? -eq 0 ]; then
    echo "转换成功! PDF文件已保存为: $output_file"
    # 在macOS上，使用open命令打开生成的PDF文件
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "正在打开PDF文件..."
        open "$output_file"
    fi
else
    echo "转换失败! 请检查错误信息"
    exit 1
fi
