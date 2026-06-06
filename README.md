# Paper Reader (Web)

Web paper-reading manager scaffold built with `Vue3 (frontend)` + `Flask (backend)` + `MongoDB`.

## 1. Required tools

1. Python 3.11+
2. Node.js 20+ (npm included)
3. MongoDB 7+
4. Git

Optional:
1. Docker Desktop (if you want to run Mongo/Redis in containers)
2. Redis 7+ (reserved for future OCR/Celery queue)

## 2. Backend setup

```powershell
cd backend
Copy-Item .env.example .env
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3 -m pip install -r requirements.txt
py -3 run.py
```

Backend URL: `http://localhost:5000`

Health check:
- `GET http://localhost:5000/api/v1/health`

## 3. Frontend setup

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

Frontend URL: `http://localhost:5173`

## 4. Auth and email verification

Implemented endpoints:
- `POST /api/v1/auth/send-code`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

Email verification supports SMTP. Configure in `backend/.env`:

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_user
SMTP_PASSWORD=your_password
SMTP_FROM_EMAIL=your_mail@example.com
SMTP_USE_TLS=true
```

Common SMTP examples:
- QQ Mail: `SMTP_HOST=smtp.qq.com`, `SMTP_PORT=587`
- 163 Mail: `SMTP_HOST=smtp.163.com`, `SMTP_PORT=587`
- Gmail: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`

You usually need an SMTP authorization code instead of your mailbox login password.

Development shortcut:
- `ALLOW_DEBUG_EMAIL_CODE=true` returns `debug_code` in response when SMTP is not configured.

Built-in development account (auto-created at startup unless disabled):
- Username: `111`
- Password: `111`

Config switches:
- `DEMO_ACCOUNT_ENABLED=true`
- `DEMO_ACCOUNT_USERNAME=111`
- `DEMO_ACCOUNT_PASSWORD=111`
- `DEMO_ACCOUNT_EMAIL=111@example.local`

## 5. Current core features

- Dynamic login/register page
- Email code verification registration
- Token-based login auth guard
- Protected API routes for papers/folders/providers/translations/agent
- Paper list and dual-pane reader shell
- Paper sorting options:
  - by created time (desc/asc)
  - by last-opened time (desc/asc)
- PDF upload endpoint and storage:
  - `POST /api/v1/papers/upload` (`multipart/form-data`, field name: `file`)
  - served at `/uploads/<user_id>/<uuid>.pdf`
- Paper management actions:
  - delete paper (`DELETE /api/v1/papers/{paper_id}`)
  - assign paper to existing folder (`PATCH /api/v1/papers/{paper_id}`, `folder_id`)
  - create new folder and assign from the dashboard UI
- Translation provider config and translation API stub integration
- Local offline visual-region extraction for uploaded PDFs (hybrid mode):
  - extract figures/regions: `POST /api/v1/papers/{paper_id}/figures/extract`
    - body options: `force`, `include_embedded_images`, `include_tables`, `include_boxed_text`, `include_table_text_strategy`, `enable_ocr_layout`, `ocr_layout_lang`, `ocr_layout_use_gpu`
  - list extracted figures: `GET /api/v1/papers/{paper_id}/figures`
  - update figure note/tags: `PATCH /api/v1/papers/{paper_id}/figures/{figure_id}`
- Optional OCR layout second-stage (for borderless tables / scanned PDFs):
  - Install locally: `pip install paddleocr paddlepaddle`
  - Then set in `backend/.env`:
    - `OCR_LAYOUT_ENABLED_DEFAULT=true`
    - `OCR_LAYOUT_LANG=en`
    - `OCR_LAYOUT_USE_GPU=false`
- OCR and agent search stub endpoints (for future implementation)

## 引用助手功能

引用助手用于把已导入文献生成可复制的引用文本。用户可以从文献库中选择一篇或多篇文献，选择引用格式后一次生成带编号的引用结果，每条引用都会带有 `[1]`、`[2]`、`[3]` 这样的编号。

支持的引用格式：
- GB/T 7714
- APA
- IEEE

基本使用步骤：
1. 在文献库中导入论文 PDF。
2. 进入“引用助手”页面。
3. 勾选需要生成引用的一篇或多篇文献。
4. 选择引用格式（GB/T 7714、APA 或 IEEE）。
5. 点击“生成引用”。
6. 使用“复制单条引用”或“复制全部引用”复制结果。

PDF 元数据解析：
- 上传 PDF 后，后端会尝试读取 PDF 前几页文本，并提取标题、作者、年份、来源等引用元数据。
- 中文论文会尝试识别“题目：”“作者：”“引用格式：”等信息。
- 英文论文会尝试识别首页标题、作者、DOI、arXiv 编号和年份。
- 引用生成时会优先使用 PDF 自动解析出的元数据；如果解析失败或字段缺失，则回退使用用户手动填写的标题、作者、来源等信息。

## 学术 AI 模块

学术 AI 是一个相对独立的 AI 工作台页面，可从顶部导航、文献库左侧工作区入口、论文卡片的“AI 速读”按钮或阅读器中的“学术 AI 分析”入口进入。页面围绕持续对话设计，主区域展示用户提问和 AI 回复，左侧工具栏用于切换论文上下文、任务模板、模型设置和历史对话。

核心能力：
- 论文上下文：支持搜索并选择 0-3 篇论文，按需启用文献信息、PDF 摘要、高亮笔记和图表说明。
- 快捷任务：内置论文速读、方法拆解、创新点与不足、汇报提纲、多篇对比和自定义提问。
- 模型设置：复用账号中配置的 LLM Provider，并支持中文或英文输出。
- 多轮会话：历史对话按更新时间排序，切换后会恢复完整消息流，后续提问会继续追加到同一会话。
- 历史管理：历史卡片支持右键重命名、归档和删除；已归档对话可通过弹窗查看，并支持还原或删除。
- Markdown 阅读：AI 回复支持 Markdown 渲染、来源展开、复制 Markdown 和重新生成。

使用建议：
1. 先在文献库导入论文 PDF，并在账号设置中配置 LLM Provider。
2. 从文献库直接点击“AI 速读”，或进入“学术 AI”页面后手动选择论文上下文。
3. 选择快捷任务或在底部输入框中直接提问。
4. 在历史工具栏中切换、重命名、归档或恢复对话。

## 6. Notes

- The backend now serializes nested Mongo `ObjectId` safely, fixing `ObjectId is not JSON serializable`.
- Data is scoped by authenticated user (`user_id`) for isolation.

## 7. Next steps

1. Replace iframe with PDF.js text selection layer.
2. Add file upload and PDF storage mapping.
3. Add OCR worker pipeline (Celery + Redis).
4. Add metadata extraction and full-text search.
# -
