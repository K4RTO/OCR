# OCR 发货单号智能识别系统

<div align="center">

基于 **MinerU** 和 **PaddleOCR** 的智能 PDF 发货单号识别系统

支持服务器部署 | 支持批量处理 | 自动重命名 | 可视化标注

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [功能特点](#功能特点)
- [技术架构](#技术架构)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
  - [服务器部署（Linux）](#服务器部署linux)
  - [本地开发（macOS）](#本地开发macos)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [维护管理](#维护管理)
- [更新日志](#更新日志)

---

## 项目简介

这是一个专门用于从PDF发货单中自动提取发货单号的智能OCR识别系统。系统采用服务器-客户端架构，部署在Linux服务器上后，团队成员可以通过浏览器访问使用，无需在本地配置复杂的开发环境。

### 核心功能

- **智能区域识别**: 优先识别发货单特定区域（前300px），失败后自动全页识别
- **高精度OCR**: 基于PaddleOCR PyTorch版，识别准确率高
- **批量处理**: 支持一次性上传多个PDF文件并批量识别
- **自动重命名**: 按识别出的发货单号自动重命名文件
- **可视化标注**: 生成带识别框的图片，红色高亮显示发货单号
- **文件管理**: 批量下载、自动清理等完善的文件管理功能

---

## 功能特点

### ✨ 智能识别

- **两步识别策略**
  - 第一步：快速识别发货单号所在区域（Y坐标 300-500px）
  - 第二步：如失败则自动全页识别
- **正则匹配**: 支持多种发货单号格式
  - `发货单号: XXXXX`
  - `发货单: XXXXX`
  - 自动提取字母数字组合

### 📦 批量处理

- 支持同时上传多个PDF文件
- 并发处理，提高处理效率
- 实时显示处理进度
- 表格化展示所有识别结果

### 🎨 可视化标注

- 生成高清标注图片
- 绿色框：普通识别文本
- 红色框：发货单号（高亮显示）
- 支持点击查看完整标注图片

### 📁 文件管理

- **自动重命名**: 按发货单号重命名文件（如 `SHIP123456.pdf`）
- **批量下载**: 一键打包下载所有处理完成的文件
- **自动清理**: 定时清理临时文件，节省存储空间
  - Input目录: 每5分钟清理一次
  - Output目录: 每天凌晨00:00清理
  - Downloads目录: 每5分钟清理超过10分钟的压缩包

### 🌐 服务器部署

- 基于Gradio Web界面，跨平台访问
- 支持局域网和公网访问
- 自动检测操作系统并适配配置
  - macOS: 本地开发模式（127.0.0.1:8143）
  - Linux: 服务器模式（0.0.0.0:8143）

---

## 技术架构

### 核心技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **OCR引擎** | PaddleOCR | PyTorch实现 | 中文文字识别 |
| **Web框架** | Gradio | 5.49.1 | Web界面 |
| **PDF处理** | MinerU + pypdfium2 | - | PDF解析与渲染 |
| **深度学习** | PyTorch | 2.9 | 模型推理 |
| **定时任务** | APScheduler | 3.10.4 | 自动清理 |

### OCR模型

本项目使用PaddleOCR的预训练模型：

- **检测模型**: `ch_PP-OCRv5_det_infer.pth` (15MB)
  - 用于检测图像中的文本区域
  - 输出文本框坐标

- **识别模型**: `ch_PP-OCRv4_rec_server_doc_infer.pth` (101MB)
  - 用于识别文本框中的具体文字
  - 服务器版模型，准确率更高

**总模型大小**: ~110MB（已内置在项目中）

### 目录映射

```
工作流程：
用户上传 → input/ → OCR识别 → output/ → 批量下载 → downloads/
                          ↓
                      debug/ocr_annotated/ (可视化标注图片)
```

---

## 系统要求

### 服务器环境（Linux）

| 项目 | 要求 | 推荐 |
|------|------|------|
| **操作系统** | Ubuntu 20.04+ / CentOS 7+ | Ubuntu 22.04 LTS |
| **Python** | 3.10+ | 3.12 |
| **内存** | 4GB+ | 8GB+ |
| **磁盘空间** | ~5GB | ~10GB |
| **端口** | 8143可访问 | - |
| **网络** | 稳定网络连接 | 国内镜像加速 |

### 本地开发环境（macOS）

| 项目 | 要求 |
|------|------|
| **操作系统** | macOS 11+ |
| **Python** | 3.10+ |
| **内存** | 8GB+ |

### 依赖包数量与大小

- **依赖包数量**: 约150个Python包
- **虚拟环境大小**: 3-5GB
- **首次安装时间**: 10-20分钟（取决于网络速度）

---

## 快速开始

### 服务器部署（Linux）

#### 方法一：一键自动部署（推荐）

```bash
# 1. 上传项目到服务器
scp -r OCR/ user@server_ip:/home/user/

# 2. SSH连接到服务器
ssh user@server_ip

# 3. 进入项目目录
cd /home/user/OCR

# 4. 赋予执行权限
chmod +x setup.sh run.sh

# 5. 运行自动配置脚本
./setup.sh
```

**setup.sh 自动完成的工作：**
- ✅ 检测 Python 3.10+ 是否已安装
- ✅ 检查系统依赖（中文字体等）
- ✅ 在 `src/.venv` 创建虚拟环境
- ✅ 升级 pip 到最新版本
- ✅ 询问是否使用清华镜像源加速
- ✅ 安装所有依赖包（约150个，3-5GB）

```bash
# 6. 启动服务
./run.sh
```

**run.sh 自动完成的工作：**
- ✅ 检查虚拟环境是否存在
- ✅ 激活虚拟环境
- ✅ 启动应用（监听 0.0.0.0:8143）

#### 方法二：使用systemd服务（生产环境推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/ocr-service.service
```

填入以下内容（根据实际路径修改）：

```ini
[Unit]
Description=OCR Shipping Invoice Extractor
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/user/OCR
Environment="PATH=/home/user/OCR/src/.venv/bin"
ExecStart=/home/user/OCR/src/.venv/bin/python /home/user/OCR/src/app/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

管理服务：

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start ocr-service

# 设置开机自启
sudo systemctl enable ocr-service

# 查看服务状态
sudo systemctl status ocr-service

# 查看日志
sudo journalctl -u ocr-service -f
```

#### 配置防火墙

确保8143端口开放：

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8143/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8143/tcp
sudo firewall-cmd --reload
```

#### 访问应用

在浏览器中访问：

```
http://<服务器公网IP>:8143
```

例如：`http://123.45.67.89:8143`

---

### 本地开发（macOS）

```bash
# 1. 进入项目目录
cd /path/to/OCR

# 2. 赋予执行权限
chmod +x setup.command run.command

# 3. 运行配置脚本
./setup.command

# 4. 启动应用
./run.command
```

启动后会自动在浏览器中打开：`http://127.0.0.1:8143`

---

## 使用指南

### 1️⃣ 上传PDF文件

1. 点击 **"上传PDF文件"** 按钮
2. 选择一个或多个PDF文件（支持批量选择）
3. 文件会自动上传到服务器

### 2️⃣ 开始识别

1. 点击 **"开始提取"** 按钮
2. 系统自动进行OCR识别
3. 实时显示处理进度

### 3️⃣ 查看结果

识别完成后，表格会显示：
- ✅ 原始文件名
- ✅ 识别出的发货单号
- ✅ 缩略图预览

**查看完整标注图片：**
- 点击表格任意行
- 右侧显示完整的标注图片
- 🟢 绿色框：普通文本
- 🔴 红色框：发货单号（高亮）

### 4️⃣ 修改单号（可选）

如果识别错误，可以直接在表格中编辑单号：
1. 双击单号单元格
2. 修改为正确的单号
3. 点击其他地方保存

### 5️⃣ 重命名文件

1. 确认所有单号无误
2. 点击 **"确认并重命名"** 按钮
3. 文件会被重命名为 `{单号}.pdf` 并移动到 `output/` 目录

### 6️⃣ 批量下载

1. 点击Output目录的 **"📥 批量下载"** 按钮
2. 系统会自动将所有文件打包成ZIP
3. ZIP文件保存在 `downloads/` 目录
4. 下载链接有效期为10分钟

### ⚠️ 文件自动清理

系统会自动清理临时文件，请注意：

| 目录 | 清理频率 | 说明 |
|------|---------|------|
| **Input** | 每5分钟 | 清理上传的原始PDF |
| **Output** | 每天00:00 | 清理处理后的PDF |
| **Downloads** | 每5分钟 | 清理超过10分钟的ZIP |

> 📌 **提示**: 页面顶部会显示下次清理时间，请及时下载需要的文件！

---

## 项目结构

```
OCR/
├── README.md                  # 项目说明文档
├── README_CN.md               # 中文版说明文档（本文档）
│
├── setup.sh                   # Linux服务器自动配置脚本
├── run.sh                     # Linux服务器启动脚本
├── requirements.txt           # Linux依赖包列表
│
├── setup.command              # macOS配置脚本
├── run.command                # macOS启动脚本
├── requirements_macos.txt     # macOS依赖包列表
│
├── input/                     # 上传文件临时存储（自动清理）
├── output/                    # 处理完成的文件（自动清理）
├── downloads/                 # ZIP下载文件（自动清理）
├── debug/                     # 调试信息
│   └── ocr_annotated/         # OCR标注图片
│
└── src/
    ├── .venv/                 # Python虚拟环境（安装时创建）
    └── app/
        ├── app.py             # 主程序（933行）
        ├── local_models/      # 本地OCR模型（110MB）
        │   └── models/
        │       └── OCR/
        │           └── paddleocr_torch/
        │               ├── ch_PP-OCRv5_det_infer.pth      # 检测模型 15MB
        │               └── ch_PP-OCRv4_rec_server_doc_infer.pth  # 识别模型 101MB
        │
        └── mineru/            # MinerU库代码
            ├── backend/       # 后端处理逻辑
            │   ├── pipeline/  # 处理流水线
            │   └── vlm/       # 视觉语言模型
            ├── cli/           # 命令行工具
            ├── model/         # 模型相关
            │   ├── layout/    # 版面分析
            │   ├── ocr/       # OCR识别
            │   └── mfr/       # 数学公式识别
            └── utils/         # 工具函数
```

---

## 配置说明

### 修改端口

编辑 `src/app/app.py` 第926行：

```python
demo.launch(
    server_name=server_name,
    server_port=8143,  # 修改为其他端口
    share=False,
    inbrowser=open_browser
)
```

### 添加访问认证

编辑 `src/app/app.py` 第924行，添加认证参数：

```python
demo.launch(
    server_name=server_name,
    server_port=8143,
    auth=("admin", "password123"),  # 添加用户名和密码
    share=False,
    inbrowser=open_browser
)
```

### 修改识别区域

编辑 `src/app/app.py` 第41行：

```python
CROP_BOX = (0, 300, 800, 500)  # (x1, y1, x2, y2)
```

参数说明：
- `x1, y1`: 左上角坐标
- `x2, y2`: 右下角坐标
- 默认识别区域：Y坐标300-500px

### 修改单号正则表达式

编辑 `src/app/app.py` 第42行：

```python
SHIPPING_ID_PATTERN = re.compile(r"发货单(?:号)?\s*[:：]\s*([A-Za-z0-9]+)")
```

### 修改清理时间

编辑 `src/app/app.py` 第888-895行：

```python
# Input目录: 每5分钟清理一次
scheduler.add_job(cleanup_input_directory, 'interval', minutes=5, id='cleanup_input')

# Output目录: 每天00:00清理
scheduler.add_job(cleanup_output_directory, 'cron', hour=0, minute=0, id='cleanup_output')

# Downloads目录: 每5分钟清理超过10分钟的文件
scheduler.add_job(cleanup_downloads_directory, 'interval', minutes=5, id='cleanup_downloads')
```

---

## 常见问题

### Q1: Python版本不满足要求？

**问题**: `setup.sh` 提示 Python 版本低于 3.10

**解决方案**:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip

# CentOS/RHEL
sudo yum install -y python3.12 python3.12-venv
```

然后重新运行 `./setup.sh`

---

### Q2: 依赖安装失败？

**问题**: pip 安装依赖时出错

**解决方案1**: 使用国内镜像源加速

```bash
# 方法1: setup.sh会自动询问是否使用镜像
./setup.sh  # 选择 'y' 使用清华镜像

# 方法2: 手动安装
source src/.venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**解决方案2**: 分步安装排查问题

```bash
source src/.venv/bin/activate

# 先升级pip
pip install --upgrade pip

# 单独安装可能有问题的包
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

---

### Q3: 端口被占用？

**问题**: 启动时提示端口8143已被占用

**排查方法**:

```bash
# 查看端口占用
sudo lsof -i :8143
# 或
sudo netstat -tulpn | grep 8143
```

**解决方案1**: 停止占用端口的进程

```bash
# 找到进程PID
sudo lsof -i :8143

# 停止进程
kill <PID>
```

**解决方案2**: [修改端口](#修改端口)

---

### Q4: 服务无法从外网访问？

**排查步骤**:

1. **检查服务是否启动**
   ```bash
   sudo systemctl status ocr-service
   # 或
   ps aux | grep app.py
   ```

2. **检查防火墙**
   ```bash
   # Ubuntu
   sudo ufw status
   sudo ufw allow 8143/tcp

   # CentOS
   sudo firewall-cmd --list-ports
   sudo firewall-cmd --permanent --add-port=8143/tcp
   sudo firewall-cmd --reload
   ```

3. **检查云服务商安全组**
   - 登录云服务器控制台
   - 找到安全组设置
   - 添加入站规则：TCP 8143端口

4. **确认监听地址**
   ```bash
   # 应该显示 0.0.0.0:8143
   sudo netstat -tulpn | grep 8143
   ```

---

### Q5: 内存不足？

**问题**: 系统提示内存不足或OOM

**最小配置**: 4GB RAM
**推荐配置**: 8GB+ RAM

**解决方案**: 创建swap交换空间

```bash
# 创建4GB swap文件
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用（添加到/etc/fstab）
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 验证
free -h
```

---

### Q6: OCR识别不到单号？

**可能原因**:

1. **单号格式不匹配**
   - 检查PDF中的格式是否为 `发货单号: XXXXX` 或 `发货单: XXXXX`
   - 如需支持其他格式，[修改正则表达式](#修改单号正则表达式)

2. **单号不在识别区域**
   - 默认优先识别Y坐标300-500px区域
   - 如失败会自动全页识别
   - 查看标注图片确认文字是否被正确识别

3. **PDF质量问题**
   - 确保PDF不是扫描件或图片质量清晰
   - 文字不要过于模糊或倾斜

**排查方法**:

1. 查看标注图片（点击表格行，右侧显示）
2. 检查绿色框是否覆盖了单号区域
3. 查看识别出的所有文字内容
4. 如有需要，手动编辑表格中的单号

---

### Q7: 首次识别很慢？

**正常现象**:

- 应用启动时会预加载OCR模型（5-10秒）
- 首次识别可能需要下载一些依赖
- 启动完成后，识别速度会很快（通常几秒内完成）

**启动日志示例**:

```
============================================================
OCR - 服务器版启动中...
============================================================
✓ 目录初始化完成

正在预加载 OCR 模型...
✓ OCR 模型加载成功

正在启动定时清理任务...
✓ 定时清理任务已启动
  - Input目录: 每5分钟清理一次
  - Output目录: 每天00:00清理
  - Downloads目录: 每5分钟清理超过10分钟的文件

正在启动 Web 服务...
============================================================
服务器模式 (Linux)
访问地址: http://0.0.0.0:8143
外网访问: http://<服务器IP>:8143
============================================================
Running on local URL:  http://0.0.0.0:8143
```

---

### Q8: 如何查看日志？

**方法1**: systemd服务日志

```bash
# 实时查看
sudo journalctl -u ocr-service -f

# 查看最近100行
sudo journalctl -u ocr-service -n 100

# 查看今天的日志
sudo journalctl -u ocr-service --since today
```

**方法2**: nohup日志

```bash
# 如果使用nohup启动
tail -f ocr.log
```

**方法3**: 前台运行查看实时输出

```bash
source src/.venv/bin/activate
python src/app/app.py
```

---

### Q9: 如何停止服务？

**方法1**: systemd服务

```bash
sudo systemctl stop ocr-service
```

**方法2**: 查找进程并停止

```bash
# 查找进程
ps aux | grep app.py

# 停止进程
kill <PID>

# 强制停止
kill -9 <PID>
```

**方法3**: 前台运行时按 `Ctrl+C`

---

### Q10: 下载的ZIP文件损坏？

**可能原因**:

1. ZIP文件超过10分钟已被自动清理
2. 下载过程中网络中断

**解决方案**:

1. 重新点击"批量下载"生成新的ZIP
2. 在10分钟内完成下载
3. 检查网络连接稳定性

---

## 维护管理

### 更新代码

```bash
cd /path/to/OCR

# 如果使用git
git pull

# 重启服务
sudo systemctl restart ocr-service
```

### 清理磁盘空间

```bash
# 手动清理上传和输出目录
rm -rf input/* output/* downloads/*

# 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 清理调试文件
rm -rf debug/*
```

### 监控资源使用

```bash
# 查看CPU和内存
htop

# 查看磁盘使用
df -h

# 查看各目录大小
du -sh input/ output/ downloads/ debug/ src/.venv/

# 查看进程资源占用
ps aux | grep app.py
```

### 日志轮转

创建日志轮转配置（如使用nohup）：

```bash
sudo nano /etc/logrotate.d/ocr-service
```

添加以下内容：

```
/path/to/OCR/ocr.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 your_username your_username
}
```

### 数据备份

```bash
# 备份输出文件
tar -czf ocr_backup_$(date +%Y%m%d).tar.gz output/

# 备份配置文件
cp src/app/app.py src/app/app.py.backup
```

---

## 安全建议

### 1. 配置HTTPS（推荐）

使用Nginx反向代理并启用SSL：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8143;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 添加访问认证

参考[配置说明 - 添加访问认证](#添加访问认证)

### 3. 限制上传文件大小

编辑 `src/app/app.py`，在Gradio组件中添加：

```python
file_input = gr.File(
    label="上传PDF文件",
    file_count="multiple",
    file_types=[".pdf"],
    max_file_size="50MB"  # 限制单个文件50MB
)
```

### 4. 定期更新依赖

```bash
source src/.venv/bin/activate
pip list --outdated
pip install --upgrade <package_name>
```

### 5. 配置防火墙规则

```bash
# 只允许特定IP访问
sudo ufw allow from 192.168.1.0/24 to any port 8143

# 或使用iptables
sudo iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 8143 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8143 -j DROP
```

---

## 更新日志

### v2.0 (2025-11-21) - 服务器版

**新功能**:
- ✅ 改为服务器部署架构，支持外网访问
- ✅ 配置端口8143，允许0.0.0.0访问（Linux）
- ✅ 添加批量下载功能（ZIP打包到downloads目录）
- ✅ 实现自动定时清理机制

**自动清理策略**:
- Input目录：每5分钟清理一次
- Output目录：每天00:00清理
- Downloads目录：每5分钟清理超过10分钟的文件

**部署优化**:
- ✅ 添加Linux自动部署脚本（setup.sh / run.sh）
- ✅ 移除Windows客户端代码，保留macOS开发环境
- ✅ 更新为Linux服务器部署文档

**UI改进**:
- ✅ 显示清理时间表在页面顶部
- ✅ 应用深色主题
- ✅ 紫色渐变状态背景

---

### v1.0 (2025-11-20)

**核心功能**:
- ✅ 实现智能OCR识别
- ✅ 发货单号自动提取
- ✅ 支持批量处理
- ✅ 自动重命名文件
- ✅ 可视化文件管理器

**跨平台支持**:
- ✅ Windows自动配置脚本
- ✅ macOS自动配置脚本

---

## 技术细节

### OCR识别流程

```
PDF文件
  ↓
转换为图片（pypdfium2）
  ↓
区域裁剪（优先识别300-500px）
  ↓
文字检测（ch_PP-OCRv5_det）
  ↓
文字识别（ch_PP-OCRv4_rec）
  ↓
正则匹配提取单号
  ↓
生成标注图片
  ↓
返回识别结果
```

### 性能优化

- **模型预加载**: 应用启动时就加载OCR模型到内存
- **懒加载**: OCR模型采用单例模式，全局共享
- **并发处理**: 支持多文件并发识别
- **图片缓存**: 标注图片自动缓存到debug目录

### 依赖包分类

核心依赖（前20个）：

```
torch==2.9.0              # 深度学习框架
gradio==5.49.1            # Web界面
paddleocr                 # OCR引擎
pypdfium2                 # PDF渲染
pillow                    # 图像处理
numpy                     # 数值计算
pandas                    # 数据处理
opencv-python             # 计算机视觉
onnxruntime              # 模型推理
transformers             # Transformer模型
huggingface-hub          # 模型下载
apscheduler              # 定时任务
fastapi                  # API框架
pydantic                 # 数据验证
aiohttp                  # 异步HTTP
requests                 # HTTP请求
beautifulsoup4           # HTML解析
lxml                     # XML解析
pyyaml                   # YAML解析
python-multipart         # 文件上传
```

---

## 许可证

本项目基于以下开源组件构建：

- **MinerU**: Apache License 2.0
- **PaddleOCR**: Apache License 2.0
- **Gradio**: Apache License 2.0
- **PyTorch**: BSD 3-Clause License

---

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

---

## 联系方式

如有问题或建议，欢迎反馈。

---

## 致谢

感谢以下开源项目：

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - 百度开源的OCR工具
- [MinerU](https://github.com/opendatalab/MinerU) - PDF解析工具
- [Gradio](https://gradio.app/) - 快速构建Web界面
- [PyTorch](https://pytorch.org/) - 深度学习框架

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star！**

</div>
