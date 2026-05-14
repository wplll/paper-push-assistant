# MMOT Paper Pusher - 多模态目标跟踪论文每日自动推送系统

每天自动从 [Awesome-Multimodal-Object-Tracking](https://github.com/983632847/Awesome-Multimodal-Object-Tracking) 仓库中筛选 3–5 篇未推送过的论文，调用 DeepSeek API 生成中文详细解读，通过邮件发送给你。

## 功能特性

- 自动拉取 GitHub 仓库 README，解析多模态目标跟踪相关论文
- 智能去重：基于标题+URL 的 SHA-256 哈希，避免重复推送
- 智能排序：优先推送新年份、有代码、关键词匹配度高的论文
- DeepSeek LLM 中文论文解读：包括核心问题、方法概述、创新点、实验分析等
- 美观 HTML 邮件推送，支持多个收件人
- 元信息自动补全：arXiv 论文自动获取摘要和作者信息
- GitHub Actions 每日定时执行，自动更新推送历史

## 项目结构

```
.
├── .github/workflows/daily.yml   # GitHub Actions 定时任务
├── src/
│   ├── __init__.py
│   ├── main.py                   # 主入口，编排整个流程
│   ├── config.py                 # 集中配置管理
│   ├── fetch_readme.py           # 拉取 README
│   ├── parse_papers.py           # 解析论文条目
│   ├── enrich_metadata.py        # 元信息补全 (arXiv API)
│   ├── ranker.py                 # 论文排序打分
│   ├── storage.py                # 去重与历史管理
│   ├── summarize.py              # LLM 论文解读
│   ├── email_sender.py           # SMTP 邮件发送
│   ├── render_email.py           # HTML 邮件渲染
│   └── llm/
│       ├── __init__.py
│       ├── base.py               # LLM 抽象基类
│       └── deepseek_provider.py  # DeepSeek API 实现
├── tests/
│   ├── test_parse_papers.py
│   ├── test_storage.py
│   └── test_ranker.py
├── data/
│   └── sent_history.json         # 已推送论文记录
├── .env.example                  # 环境变量模板
├── .gitignore
├── requirements.txt
└── README.md
```

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的真实配置（见下方说明）。

### 3. 运行

```bash
python -m src.main
```

### 4. 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## .env 配置说明

| 变量名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API 密钥 | `sk-xxx` |
| `DEEPSEEK_BASE_URL` | 否 | API 地址，默认官方地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 否 | 模型名称，默认 `deepseek-chat` | `deepseek-chat` |
| `SMTP_HOST` | 是 | SMTP 服务器 | `smtp.qq.com` |
| `SMTP_PORT` | 否 | SMTP 端口，默认 465 | `465` |
| `SMTP_USER` | 是 | SMTP 用户名 | `you@qq.com` |
| `SMTP_PASSWORD` | 是 | SMTP 授权码 | `your-auth-code` |
| `EMAIL_FROM` | 是 | 发件人地址 | `you@qq.com` |
| `EMAIL_TO` | 是 | 收件人，多人用逗号分隔 | `a@x.com,b@y.com` |
| `PAPERS_PER_DAY` | 否 | 每日推送论文数，默认 5 | `5` |
| `MIN_PAPERS_PER_DAY` | 否 | 最少推送数，默认 3 | `3` |
| `SKIP_EMPTY_EMAIL` | 否 | 无新论文时是否跳过邮件，默认 true | `true` |
| `REQUEST_TIMEOUT` | 否 | 网络请求超时秒数，默认 30 | `30` |
| `README_RAW_URL` | 否 | README 原始地址 | 见 .env.example |
| `SENT_HISTORY_PATH` | 否 | 历史记录路径 | `data/sent_history.json` |

## GitHub Actions 部署步骤

### 1. Fork 或创建仓库

将本项目推送到你的 GitHub 仓库。

### 2. 设置 GitHub Secrets

进入仓库 → Settings → Secrets and variables → Actions → New repository secret，添加以下 Secrets：

| Secret 名称 | 说明 |
|-------------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | (可选) API 地址 |
| `DEEPSEEK_MODEL` | (可选) 模型名 |
| `SMTP_HOST` | SMTP 服务器地址 |
| `SMTP_PORT` | SMTP 端口 |
| `SMTP_USER` | SMTP 用户名 |
| `SMTP_PASSWORD` | SMTP 授权码 |
| `EMAIL_FROM` | 发件人邮箱 |
| `EMAIL_TO` | 收件人邮箱 |

### 3. 设置 GitHub Variables (可选)

进入 Settings → Secrets and variables → Actions → Variables，可设置：

| Variable 名称 | 说明 | 默认值 |
|--------------|------|--------|
| `PAPERS_PER_DAY` | 每日推送数量 | 5 |
| `SKIP_EMPTY_EMAIL` | 无新论文时跳过邮件 | true |

### 4. 自动运行

Workflow 默认每天 UTC 01:00（北京时间 09:00）自动运行。

### 5. 手动触发

进入 Actions → Daily Paper Push → Run workflow，点击即可手动触发。

## 如何查看推送历史

推送记录保存在 `data/sent_history.json` 中。每次成功推送后，GitHub Actions 会自动将更新的文件 commit 回仓库。

你也可以在 GitHub 仓库页面查看该文件的提交历史。

## 常见问题

### DeepSeek API 调用失败怎么办？

- 检查 `DEEPSEEK_API_KEY` 是否正确
- 检查 `DEEPSEEK_BASE_URL` 是否可访问
- 代码内置 2 次重试机制；如果仍然失败，会使用 fallback 摘要（标注"LLM 调用失败"）
- 也可以更换为其他 OpenAI 兼容 API（如 Moonshot、Zhipu 等）

### 邮件发不出去怎么办？

- QQ 邮箱需要使用**授权码**而非登录密码
- 确认 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD` 配置正确
- 465 端口使用 SSL，587 端口使用 STARTTLS
- 检查发件邮箱是否开启了 SMTP 服务

### 为什么没有新论文？

- 所有已收录论文可能都已推送过
- 检查 `data/sent_history.json` 中的记录数
- 可以手动编辑该文件删除部分记录来重新推送
- 等待源仓库更新新论文

### 如何调整每天推送数量？

设置环境变量 `PAPERS_PER_DAY`（默认 5）和 `MIN_PAPERS_PER_DAY`（默认 3）。

### 如何更换模型？

设置环境变量 `DEEPSEEK_MODEL`。只要是 OpenAI 兼容的 API 都可以使用，例如：

- `deepseek-chat`（DeepSeek-V3）
- `deepseek-reasoner`（DeepSeek-R1）
- `moonshot-v1-8k`（Moonshot）
- `glm-4`（Zhipu）

同时需要修改 `DEEPSEEK_BASE_URL` 对应的 API 地址。

### 如何更换论文来源？

修改环境变量 `README_RAW_URL` 指向新的 raw README 地址。注意新仓库的 Markdown 结构可能需要调整解析逻辑。
