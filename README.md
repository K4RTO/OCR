# OCR - Linux服务器版

基于 MinerU 和 PaddleOCR 的智能 PDF 发货单号识别系统，部署在服务器上供团队成员通过浏览器访问使用。

## 功能特点

- **智能OCR识别**：使用 PaddleOCR (PyTorch版本) 提取发货单号
- **区域裁剪优化**：优先识别指定区域，失败后自动全页识别
- **可视化标注**：生成带识别框的图片，红色高亮单号
- **批量处理**：支持一次上传多个 PDF 文件
- **自动重命名**：按发货单号重命名并整理到输出目录
- **批量下载**：一键下载所有处理完成的文件
- **自动清理**：Input目录每5分钟清理，Output目录每天00:00清理
- **服务器部署**：通过公网IP+端口访问，无需本地配置环境

## 系统要求

- **操作系统**：Linux (Ubuntu 20.04+ 推荐)
- **Python**：3.10+ (推荐 3.12)
- **内存**：建议 8GB+ RAM
- **磁盘空间**：~5GB（虚拟环境 + 依赖 + 模型）
- **端口**：8143端口可访问

## 服务器部署指南

### 快速部署（推荐）

本项目提供了自动化部署脚本，一键完成环境配置：

#### 1. 准备工作

```bash
# 删除本地开发环境（如果存在）
rm -rf src/.venv
```

#### 2. 上传项目到服务器

```bash
# 方法1: 使用scp上传整个项目
scp -r Hichain-OCR/ user@server_ip:/home/user/

# 方法2: 使用git（如果有仓库）
ssh user@server_ip
git clone <repository_url>
```

#### 3. 运行自动配置脚本

```bash
# SSH连接到服务器
ssh user@server_ip

# 进入项目目录
cd /home/user/Hichain-OCR

# 添加执行权限
chmod +x setup.sh run.sh

# 运行自动配置脚本
./setup.sh
```

**setup.sh 自动完成以下工作：**
- ✅ 检测 Python 3.10+ 是否已安装（未安装会提示）
- ✅ 检查系统依赖（中文字体等）
- ✅ 在 `src/.venv` 创建虚拟环境
- ✅ 自动激活虚拟环境
- ✅ 升级 pip 到最新版本
- ✅ 询问是否使用清华镜像源加速下载
- ✅ 安装 requirements.txt 中的所有依赖（约150个包，3-5GB，10-20分钟）

#### 4. 启动服务

```bash
# 使用启动脚本（前台运行）
./run.sh
```

**run.sh 自动完成：**
- ✅ 检查虚拟环境是否存在
- ✅ 激活虚拟环境
- ✅ 启动应用（监听 0.0.0.0:8143）

---

### 手动部署（可选）

如果需要手动控制每一步，可以按以下流程操作：

#### 1. 环境准备

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装Python 3.12和依赖
sudo apt install -y python3.12 python3.12-venv python3-pip

# 安装中文字体 (可选，用于OCR标注图片)
sudo apt install -y fonts-wqy-microhei fonts-noto-cjk
```

#### 2. 上传项目文件

将项目文件上传到服务器（使用scp、sftp或git）：

```bash
# 方法1: 使用scp上传
scp -r Hichain-OCR/ user@server_ip:/path/to/

# 方法2: 使用git（如果有仓库）
git clone <repository_url>
```

#### 3. 创建虚拟环境并安装依赖

```bash
cd /path/to/Hichain-OCR

# 创建虚拟环境
python3.12 -m venv src/.venv

# 激活虚拟环境
source src/.venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖（使用清华镜像加速）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**注意**：首次安装依赖大约需要10-20分钟，下载约3-5GB数据。

#### 4. 配置防火墙

确保8143端口开放：

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8143/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8143/tcp
sudo firewall-cmd --reload
```

#### 5. 启动服务

**方法1: 使用启动脚本（推荐）**

```bash
# 前台运行
./run.sh

# 后台运行
nohup ./run.sh > ocr.log 2>&1 &

# 查看日志
tail -f ocr.log
```

**方法2: 直接启动**

```bash
source src/.venv/bin/activate
python src/app/app.py
```

**方法3: 使用nohup后台运行**

```bash
source src/.venv/bin/activate
nohup python src/app/app.py > ocr.log 2>&1 &
```

**方法4: 使用systemd服务（推荐生产环境）**

创建服务文件：

```bash
sudo nano /etc/systemd/system/hichain-ocr.service
```

填入以下内容：

```ini
[Unit]
Description=Hichain OCR Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Hichain-OCR
Environment="PATH=/path/to/Hichain-OCR/src/.venv/bin"
ExecStart=/path/to/Hichain-OCR/src/.venv/bin/python /path/to/Hichain-OCR/src/app/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start hichain-ocr

# 设置开机自启
sudo systemctl enable hichain-ocr

# 查看服务状态
sudo systemctl status hichain-ocr

# 查看日志
sudo journalctl -u hichain-ocr -f
```

### 6. 访问应用

启动成功后，通过浏览器访问：

```
http://<服务器公网IP>:8143
```

例如：`http://123.45.67.89:8143`

---

## 使用说明

### 1. 上传和提取

1. 在浏览器中打开应用
2. 点击 **"上传PDF文件"** 按钮，选择一个或多个 PDF
3. 点击 **"开始提取"** 按钮
4. 等待 OCR 识别完成

### 2. 查看结果

- 表格显示：原始文件名、提取的单号、缩略图
- **点击表格任意行**，右侧显示完整标注图片
- 🟢 绿色框：普通识别文本
- 🔴 红色框：发货单号（高亮显示）

### 3. 修改单号（可选）

- 如果识别错误，可以直接在表格中编辑单号

### 4. 重命名和整理

- 点击 **"确认并重命名"** 按钮
- 文件会被重命名为 `{单号}.pdf` 并保存到 `output` 目录

### 5. 批量下载

- 点击Output目录的 **"📥 批量下载"** 按钮
- 所有文件会打包成ZIP文件供下载

### 6. 文件自动清理

⚠️ **重要提示**：

- **Input 目录**：每5分钟自动清理一次（删除上传的原始文件）
- **Output 目录**：每天00:00自动清理（删除处理后的文件）
- **Downloads 目录**：每5分钟清理超过10分钟的ZIP文件
- 页面顶部会显示下次清理时间
- **下载链接有效期为10分钟，请及时下载处理完成的文件！**

---

## 项目结构

```
Hichain-OCR/
├── setup.sh                   # Linux服务器自动配置脚本
├── run.sh                     # Linux服务器启动脚本
├── requirements.txt           # Linux服务器依赖清单
├── requirements_macos.txt     # macOS开发环境依赖清单
├── setup.command              # macOS自动配置脚本
├── run.command                # macOS启动脚本
├── README.md                  # 本文档
├── input/                     # 上传文件存储目录（每5分钟清理）
├── output/                    # 处理结果输出目录（每天00:00清理）
├── downloads/                 # ZIP文件下载目录（每5分钟清理超过10分钟的文件）
├── debug/                     # 调试信息（自动清理）
└── src/
    ├── .venv/                 # 虚拟环境（部署时创建）
    └── app/
        ├── app.py             # 主程序
        ├── local_models/      # 本地模型文件 (110MB)
        └── mineru/            # MinerU 库代码
```

---

## 技术栈

- **OCR 引擎**：PaddleOCR (PyTorch实现)
- **模型**：
  - 检测模型：ch_PP-OCRv5_det_infer.pth (15MB)
  - 识别模型：ch_PP-OCRv4_rec_server_doc_infer.pth (101MB)
- **Web 框架**：Gradio 5.49
- **PDF 处理**：MinerU、pypdfium2
- **深度学习**：PyTorch 2.9、ONNX Runtime
- **定时任务**：APScheduler

---

## 常见问题

### Q1: setup.sh 提示 Python 未安装？

安装 Python 3.10 或更高版本：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip

# CentOS/RHEL
sudo yum install -y python3.12 python3.12-venv
```

然后重新运行 `./setup.sh`

### Q2: setup.sh 执行权限被拒绝？

添加执行权限：

```bash
chmod +x setup.sh run.sh
```

### Q3: 依赖安装失败？

**网络问题**：使用国内镜像源

```bash
# 重新运行 setup.sh 时选择 'y' 使用清华镜像
./setup.sh

# 或手动安装
source src/.venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**权限问题**：确保使用虚拟环境，避免sudo安装

### Q4: run.sh 提示虚拟环境不存在？

先运行 setup.sh 创建虚拟环境：

```bash
./setup.sh
```

### Q2: 端口被占用？

查看8143端口占用：

```bash
sudo lsof -i :8143
# 或
sudo netstat -tulpn | grep 8143
```

如需更改端口，修改 `src/app/app.py` 第874行：

```python
server_port=8143,  # 改为其他端口
```

### Q3: 服务无法从外网访问？

1. 检查防火墙是否开放端口
2. 检查云服务商安全组规则（如阿里云、腾讯云）
3. 确认server_name设置为 `"0.0.0.0"`

### Q4: 内存不足？

建议配置：
- 最小：4GB RAM
- 推荐：8GB+ RAM
- 如果内存不足，可以配置swap：

```bash
# 创建4GB swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q5: 如何查看运行日志？

```bash
# 方法1: 使用systemd服务
sudo journalctl -u hichain-ocr -f

# 方法2: 使用nohup
tail -f ocr.log

# 方法3: 直接运行查看实时输出
source src/.venv/bin/activate
python src/app/app.py
```

### Q6: 如何停止服务？

```bash
# 方法1: systemd服务
sudo systemctl stop hichain-ocr

# 方法2: 查找进程并kill
ps aux | grep app.py
kill <PID>
```

### Q7: 首次识别很慢？

- 应用启动时会自动加载 OCR 模型（5-10 秒）
- 启动完成后，识别速度很快
- 首次运行可能需要下载一些依赖

### Q8: 识别不到单号？

检查 PDF 文件：
- 发货单号格式：`发货单号: XXXXX` 或 `发货单: XXXXX`
- 如果单号不在前 300 像素区域，会自动全页识别
- 查看标注图片，确认 OCR 是否正确识别文字

---

## 维护管理

### 更新代码

```bash
cd /path/to/Hichain-OCR
git pull  # 如果使用git

# 重启服务
sudo systemctl restart hichain-ocr
```

### 清理磁盘空间

```bash
# 手动清理input/output目录
rm -rf input/* output/*

# 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 监控资源使用

```bash
# 查看CPU和内存
htop

# 查看磁盘使用
df -h

# 查看目录大小
du -sh input/ output/ debug/
```

---

## 安全建议

1. **配置反向代理**（Nginx）并启用HTTPS
2. **添加访问认证**（Gradio支持basic auth）
3. **定期更新系统和依赖**
4. **限制上传文件大小**
5. **配置日志轮转**

示例：添加Gradio认证

在 `src/app/app.py` 第872行修改：

```python
demo.launch(
    server_name="0.0.0.0",
    server_port=8143,
    auth=("username", "password"),  # 添加此行
    share=False,
    inbrowser=False
)
```

---

## 许可证

本项目基于开源组件构建：
- MinerU: Apache-2.0
- PaddleOCR: Apache-2.0
- Gradio: Apache-2.0

---

## 更新日志

### v2.0 (2025-11-21) - 服务器版

- ✅ 改为服务器部署架构，支持外网访问
- ✅ 配置端口8143，允许0.0.0.0访问（Linux）
- ✅ 添加批量下载功能（ZIP打包到downloads目录）
- ✅ 实现自动定时清理：
  - Input 目录：每5分钟清理
  - Output 目录：每天00:00清理
  - Downloads 目录：每5分钟清理超过10分钟的文件
- ✅ 显示清理时间表在UI上
- ✅ 移除Windows客户端代码，保留macOS开发环境
- ✅ 添加Linux自动部署脚本（setup.sh / run.sh）
- ✅ 更新为Linux服务器部署文档
- ✅ 应用深色主题，紫色渐变状态背景

### v1.0 (2025-11-20)

- ✅ 实现智能 OCR 识别和发货单号提取
- ✅ 支持批量处理和自动重命名
- ✅ 可视化文件管理器
- ✅ 跨平台自动配置脚本（Windows/macOS）

---

## 联系方式

如有问题或建议，欢迎反馈。
