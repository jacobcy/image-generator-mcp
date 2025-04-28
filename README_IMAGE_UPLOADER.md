# 图床上传工具使用指南

这个工具用于将本地图片上传到图床，获取图片URL供API使用。支持ImgBB和GitHub图床服务。

## 前提条件

1. 需要安装Python 3.6+
2. 需要安装`requests`库（脚本会自动安装）
3. 需要ImgBB的API密钥或GitHub个人访问令牌

## 获取API密钥

### 方式1：ImgBB API密钥

1. 注册并登录[ImgBB](https://imgbb.com/)
2. 访问[API页面](https://api.imgbb.com/)获取API密钥

### 方式2：GitHub个人访问令牌

1. 登录[GitHub](https://github.com/)
2. 访问[Personal Access Tokens](https://github.com/settings/tokens)页面
3. 点击"Generate new token"
4. 选择至少包含`repo`权限
5. 生成并复制令牌

## 配置API密钥

有两种方式配置API密钥：

### 方式1：环境变量

对于ImgBB：
```bash
export IMGBB_API_KEY="你的ImgBB API密钥"
```

对于GitHub：
```bash
export GITHUB_TOKEN="你的GitHub个人访问令牌"
```

### 方式2：.env文件

在项目根目录创建`.env`文件，添加以下内容：

```
IMGBB_API_KEY=你的ImgBB API密钥
GITHUB_TOKEN=你的GitHub个人访问令牌
```

## 使用GitHub图床前的准备

如果您选择使用GitHub作为图床，需要先创建一个仓库：

1. 登录GitHub并创建一个新的公开仓库（默认名称为`image-hosting`）
2. 初始化仓库并创建一个`images`文件夹

## 使用方法

### 上传图片到ImgBB（默认）

```bash
./upload_image.sh upload 图片路径
```

或显式指定使用ImgBB：

```bash
./upload_image.sh upload -s imgbb 图片路径
```

### 上传图片到GitHub

```bash
./upload_image.sh upload -s github 图片路径
```

可以指定仓库、分支和文件夹：

```bash
./upload_image.sh upload -s github --repo my-images --branch main --folder assets 图片路径
```

成功后会显示图片URL和其他相关信息。

### 查看上传历史

```bash
./upload_image.sh history
```

默认显示最近10条记录，可以通过`-n`参数指定显示数量：

```bash
./upload_image.sh history -n 20
```

## 在Python代码中使用

如果需要在Python代码中使用图床上传功能，可以这样导入：

### 使用ImgBB

```python
from cell_cover.utils.image_uploader import upload_to_imgbb, get_api_key

# 获取API密钥
api_key = get_api_key(service="imgbb")

# 上传图片
result = upload_to_imgbb("图片路径", api_key)

if result["success"]:
    image_url = result["url"]
    print(f"图片URL: {image_url}")
else:
    print(f"上传失败: {result.get('message')}")
```

### 使用GitHub

```python
from cell_cover.utils.image_uploader import upload_to_github, get_api_key

# 获取API密钥
github_token = get_api_key(service="github")

# 上传图片
result = upload_to_github(
    "图片路径",
    github_token,
    repo="image-hosting",  # 可选
    branch="main",        # 可选
    folder="images"        # 可选
)

if result["success"]:
    image_url = result["url"]  # CDN URL
    print(f"图片URL: {image_url}")
else:
    print(f"上传失败: {result.get('message')}")
```

## 在generate_cover.py中使用

如果需要在`generate_cover.py`中使用上传的图片作为参考图像，可以这样使用：

```bash
# 先上传图片到ImgBB
./upload_image.sh upload ./reference_image.png
# 或上传到GitHub
./upload_image.sh upload -s github ./reference_image.png
# 复制返回的URL

# 然后在创建封面时使用--cref参数
python -m cell_cover.generate_cover create -c ca -var scientific -ver v6 --cref "复制的URL"
```

注意：如果使用GitHub，请使用返回的CDN URL（以`https://cdn.jsdelivr.net/`开头的URL）作为参考图像。

## 故障排除

1. 如果遇到权限问题，请确保`upload_image.sh`有执行权限：
   ```bash
   chmod +x upload_image.sh
   ```

2. 如果遇到导入错误，请确保已安装依赖：
   ```bash
   uv pip install requests
   ```

3. 如果使用GitHub上传失败，请确保：
   - GitHub令牌有`repo`权限
   - 指定的仓库存在且为公开仓库
   - 指定的分支存在

4. 如果使用ImgBB上传失败，请检查API密钥是否正确配置。

5. 如果需要删除已上传的图片：
   - ImgBB: 使用上传后返回的删除链接
   - GitHub: 登录GitHub并手动删除文件