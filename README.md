# 滴鱼简历助手 XG Resume Studio

> 📁 本地优先的个人简历管理系统：上传证书照片 / PDF / Word，自动识别**获奖情况**与**任职情况**；
> 填好资料后用四套场景化 A4 模板一键产出简历（网页预览 / 打印存 PDF / 服务端 PDF / Word 下载）。
> 所有数据只存在你自己的电脑里。

![CI](https://github.com/MapleLloyd/xg-resume-studio/actions/workflows/ci.yml/badge.svg)
![Build EXE](https://github.com/MapleLloyd/xg-resume-studio/actions/workflows/build.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)

<!-- 截图占位：发布前请替换为真实截图（使用示例数据拍摄，勿含个人信息）
![首页](docs/screenshots/home.png)
![简历预览](docs/screenshots/resume.png)
-->

## ✨ 特性

- **材料 → 结构化条目**：证书图片自动 OCR（支持 EXIF 方向校正、手动旋转重试），
  规则提取获奖与任职候选，弹窗勾选确认后才入库；配置大模型 API 后可一键「AI 整理」
- **重复导入检测**：同一份材料（标题+时间相同）不会被录入两次
- **多份简历版本**：保研版 / 求职版 / 奖学金版…每个版本独立记忆「模板 + 主题色 + 模块显隐排序 + 各自的个人简介/自我评价」，条目数据全局共享
- **四套场景模板**：求职·经典单栏 / 保研·学术强调 / 晋升·履历时间轴 / 评优·极简黑白，
  支持 6 色主题、三档密度、七个模块自由显隐排序；简历文案可**中英文一键切换**
- **三种导出**：打印存 PDF / 服务端生成 A4 PDF / Word（个人介绍可单独导出 Word）
- **佐证文件**：每条获奖/任职可挂证书扫描件，条目删除时级联清理
- **AI 助手「小点」**：流式打字回复、可随时停止；分析简历用途、改写个人简介（一键采纳）、优化条目描述
- **个人资料**：基本信息、证件照（3:4 裁剪）、教育/论文/项目、技能语言、**自我评价（标签 + 自由文本）**，自动保存
- **轻量档案切换**：可建多个档案给不同用途/家人室友使用，互不可见（本地档案切换，不是登录系统）
- **手机扫码直传**：局域网内扫码，手机拍证书直接进入系统（默认关闭，用前手动开启）
- **数据安全**：单文件 SQLite（WAL 并发优化）+ 每次启动自动滚动备份；API Key 仅本地存储且界面只显示掩码；局域网入口可随时关闭

## 🚀 快速开始

### 安装版（推荐，Windows）

1. 打开 [Releases 页面](https://github.com/MapleLloyd/xg-resume-studio/releases) 下载最新的 `XG-Resume-Studio-*-setup.exe`
2. 双击运行，按向导安装（会创建开始菜单与可选桌面快捷方式，无需管理员权限）
3. 卸载时程序会询问是否保留你的 `data` 数据，选「否」则彻底删除

### 绿色免安装版

1. 下载 `XG-Resume-Studio-*-win64.zip`，解压后双击「滴鱼简历助手.exe」即可使用
2. 全部数据保存在程序旁的 `data` 文件夹内；升级新版本时保留该文件夹即可
3. 首次启动如遇 SmartScreen 提示，点「更多信息 → 仍要运行」

### 从源码运行（Windows）

1. 安装 [Python 3.10–3.14](https://www.python.org/downloads/)（勾选 Add to PATH）
2. 双击 `滴鱼简历助手.bat` —— 首次运行会自动创建虚拟环境并安装依赖（几分钟，请勿关窗），然后打开浏览器
3. 按初始化向导完成配置即可使用

### macOS / Linux

```bash
git clone https://github.com/MapleLloyd/xg-resume-studio.git resume-studio && cd resume-studio
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
# 打开 http://127.0.0.1:8000
```

### 手机扫码直传

扫码直传**默认关闭**（避免公网/不可信网络下无意暴露服务）。需要时：
1. 在电脑端首页打开「手机扫码直传」开关
2. 手机连同一 Wi-Fi，扫首页二维码并输入**配对码**（首页二维码下方显示）即可拍照直传
3. 自动选错 IP 时，可在首页「手动指定局域网 IP」输入框里填写，立即生效
4. 用完后随时关掉开关；二维码链接可一键重置作废

## 🤖 配置 AI（可选）

不配置也能正常使用全部手动功能与规则提取。配置后解锁 AI 整理与小点助手：

| 服务商 | 接口地址 | 推荐模型 |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Moonshot Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Ollama（本地） | `http://127.0.0.1:11434/v1` | 你已拉取的模型 |

任何兼容 OpenAI Chat Completions 的接口均可。首页填入后点「测试连接」验证。

## 🔒 隐私说明

- 全部数据（数据库、上传文件、导出文档）仅保存在程序目录内，卸载询问是否保留
- AI 功能关闭时，没有任何数据离开你的电脑
- AI 功能启用后，相关文本只会发送到**你自己填写**的接口商；密钥仅保存在本地数据库且界面回显掩码
- 局域网模式请在可信网络中使用；默认关闭，用时再开，二维码链接可随时重置

## ❓ FAQ

- **局域网模式要配对码？** 安全设计：手机等设备首次打开需输入首页显示的 6 位配对码，30 天内免输
- **端口被占用？** `滴鱼简历助手.bat` 自动在 8000~8010 中寻找空闲端口；也可自行修改启动命令里的 `--port`
- **依赖安装慢/失败？** 默认源失败会自动改用清华镜像重试；也可手动加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`
- **识别文字很少？** 上传结果会给出具体诊断（扫描件/方向/文字层/清晰度）；可点「旋转重试」，或配置 AI 后点「AI 整理」
- **想彻底重置？** 关闭程序后删除整个 `data/` 文件夹，重启即回到全新状态
- **备份在哪？** `data/data_backups/` 下每次启动滚动保留最近 20 份，误操作可用其恢复

## 🗺️ 路线图

- [x] 服务端 PDF 导出
- [x] 多份简历版本
- [x] 简历内容英文版（模板/PDF/Word 中英切换）
- [x] 应用内更新日志
- [x] Inno Setup 安装版（含单文件 EXE 绿色版）
- [x] 个人资料「自我评价」
- [x] 小点流式对话 / 安全加固 / 上传诊断
- [ ] 更多简历模板与自定义模板市场

## 🤝 参与贡献

见 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)。提交前请确保 `pytest` 与 `ruff check` 通过。

## 📮 支持与反馈

运行环境、启动报错类问题，请先阅读 **docs/运行环境配置说明.txt**（含常见问题自查清单）。
仍无法解决请联系开发者：**maplelloyd@163.com**（请注明问题现象 + 报错截图）。

## 📄 许可证

[MIT](LICENSE)