# macOS 上将 Markdown 文件转换为正式论文格式的详细步骤

## 步骤 1：安装 Pandoc

### 安装准备
1. 打开终端
   - 在 macOS 中，打开"应用程序"文件夹
   - 然后打开"实用工具"文件夹
   - 找到并打开"终端"

2. 安装 Homebrew（如果尚未安装）
   > Homebrew 是 macOS 的包管理器，我们将使用它来安装 Pandoc 和 LaTeX。如果您已经安装了 Homebrew，请跳过此步骤。

   在终端中运行以下命令：
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   系统将提示您输入管理员密码。按照屏幕上的说明完成安装。

### 安装 Pandoc
在终端中运行以下命令：
```bash
brew install pandoc
```

### 验证安装
安装完成后，在终端中运行以下命令来验证 Pandoc 是否已成功安装：
```bash
pandoc --version
```
如果 Pandoc 已成功安装，您将看到 Pandoc 的版本信息。

## 步骤 2：安装 LaTeX

我们将使用 TeX Live 作为 LaTeX 发行版。

### 安装完整版 MacTeX
在终端中运行以下命令来安装 MacTeX：
```bash
brew install --cask mactex-no-gui
```
> 注意：由于 MacTeX 体积较大，此过程可能需要一些时间。

### （可选）安装轻量版 BasicTeX
如果您不想安装完整的 MacTeX，可以选择安装 BasicTeX，这是一个较小的 LaTeX 发行版：
```bash
brew install --cask basictex
```

安装 BasicTeX 后，您可能需要手动安装一些常用的宏包，例如：
```bash
sudo tlmgr install texlive-extra-utils
```

## 步骤 3：准备 Markdown 文件

### 创建或准备 Markdown 文件
使用任何文本编辑器（例如 TextEdit、Visual Studio Code 或 Sublime Text）创建或准备您的 Markdown 文件（例如 `background.md`）。

确保您的 Markdown 文件包含以下元素：
- 标题
- 作者姓名
- 日期
- 章节和段落
- 任何需要的公式（用 LaTeX 语法编写）
- 任何需要的引用（使用 Pandoc 的引用格式或 BibTeX）

### 准备参考文献
如果您需要在论文中包含参考文献，请创建一个 BibTeX 文件（例如 `references.bib`），其中包含您的参考文献条目。

## 步骤 4：将 Markdown 转换为 PDF

### 准备工作
1. 打开终端应用程序
2. 导航到 Markdown 文件所在的目录：
   ```bash
   cd ~/Documents
   ```

### 运行转换命令
在终端中运行 pandoc 命令，将您的 Markdown 文件转换为 PDF：
```bash
pandoc background.md -o paper.pdf \
    --from=markdown+tex_math_single_backslash \
    --to=pdf \
    --standalone \
    --template=eisvogel.tex \
    --bibliography=references.bib \
    --citeproc
```

#### 命令参数说明
- `background.md`：您的 Markdown 文件的名称
- `-o paper.pdf`：输出 PDF 文件的名称
- `--from=markdown+tex_math_single_backslash`：指定输入格式为 Markdown，并启用对单反斜杠 LaTeX 数学公式的支持
- `--to=pdf`：指定输出格式为 PDF
- `--standalone`：生成一个完整的 PDF 文件，包括序言和页眉/页脚
- `--template=eisvogel.tex`：使用 Eisvogel LaTeX 模板（如果需要）。您可以替换为您自己的模板或使用默认模板
- `--bibliography=references.bib`：指定 BibTeX 文件的名称
- `--citeproc`：处理引用

## 步骤 5：检查生成的 PDF

1. 打开 PDF 文件：找到生成的 PDF 文件（例如 `paper.pdf`）并打开它，以确保其格式正确
2. 根据需要进行调整：如果生成的 PDF 文件的格式不完全符合您的要求，您可能需要调整：
   - Markdown 文件
   - LaTeX 模板
   - Pandoc 命令选项

## 步骤 6：使用模板（可选）

### 获取模板
下载 Eisvogel 模板：
```bash
curl -L -o eisvogel.tex https://raw.githubusercontent.com/Wandmalfarbe/pandoc-latex-template/master/eisvogel.tex
```

### 配置模板
下载完成后，将 `eisvogel.tex` 文件放在：
- 您的 Markdown 文件所在的目录中，或者
- Pandoc 可以找到的目录中（例如 `~/.pandoc/templates/`）

### 使用模板
在 Pandoc 命令中使用 `--template` 选项来指定要使用的模板：
```bash
pandoc your_document.md -o output.pdf --template=eisvogel.tex
```


