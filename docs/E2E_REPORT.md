# 浏览器端到端测试报告

> 测试方式：Kimi WebBridge（Chrome 扩展 + 守护进程）直接控制真机浏览器（非无头）
> 测试时间：2026-06-16
> 工具栈：Next.js 15 + Flask + Kimi WebBridge v1.9.13
> 浏览器：用户本地 Chromium 内核浏览器

---

## 一、测试环境

| 项目 | 状态 |
| --- | --- |
| 前端 `localhost:3000` | ✅ 运行中（Next.js dev / Turbopack） |
| 后端 `127.0.0.1:8000` | ✅ 运行中（Flask） |
| 简历样本 | `苏明远2-简历-20260615.docx`（真实 docx，约 2KB） |
| JD 样本 | `AI Agent 工程师岗位要求（JD）.txt`（1979 字符） |
| Kimi WebBridge 守护进程 | ✅ 127.0.0.1:10086，扩展 fldmhcel...mligc v1.9.13 已连 |

---

## 二、核心流程用例（13 项）

| # | 用例 | 结果 | 关键证据 |
| --- | --- | :---: | --- |
| 1 | 首页 `GET /` 加载 | ✅ | 渐变标题 `HR批评简历` + "开始使用" 渲染正常 |
| 2 | 首页 CTA → `/resume` | ✅ | 点击后立即跳转 |
| 3 | `/resume` 上传区渲染 | ✅ | "拖拽或点击上传" 显示 |
| 4 | 上传 docx 简历 | ✅ | POST `/api/v1/resumes/upload` 200，navigate 到 `/jobs?resume_id=...` |
| 5 | 上传非法 `.txt` 文件 | ✅ | 红色错误框："文件\"bad.txt\"类型不支持" + 列出允许的 MIME |
| 6 | `/jobs` 空 JD 时 "下一步" 禁用 | ✅ | `button[type=submit].disabled === true` |
| 7 | 填 JD + 点 "下一步" | ✅ | 约 20s 提交，`button` 变 "已提交" + "开始优化" |
| 8 | 点 "开始优化" 流式分析 | ✅ | 约 48s 完成，navigate 到 `/dashboard` |
| 9 | Dashboard 渲染分析结果 | ✅ | 岗位分析卡 + "分析结果" 流式 markdown 完整 |
| 10 | "在可视化编辑器中继续优化" | ✅ | POST `/api/v1/resumes/improved-markdown` 200（已确认） |
| 11 | "分析另一个岗位" 打开 modal | ✅ | `<PasteJobDescription>` modal 出现 |
| 12 | "优化简历" 触发深度重审 | ✅ | 重新调用 LLM，输出换用深度 prompt（"批判？💥解析🔧建议"） |
| 13 | 移动端响应式 | ✅ | 375px 宽度下布局自适应 |

---

## 三、API 健康度（7 个端点）

| 方法 + 路径 | 状态 | 备注 |
| --- | :---: | --- |
| `GET /ping` | ✅ | 文档与代码一致 |
| `GET /api/v1/resumes?resume_id=...` | ✅ | 返回完整简历 + 解析后结构 |
| `POST /api/v1/resumes/upload` | ✅ | 接受 PDF/DOCX，2MB 限制 |
| `POST /api/v1/resumes/improve?stream=true` | ✅ | SSE 流式工作 |
| `POST /api/v1/resumes/improved-markdown` | ✅ | 提取 ```md fenced block 供 a4cv |
| `POST /api/v1/jobs/upload` | ✅ | 严格 Content-Type 校验 |
| `GET /api/v1/jobs?job_id=...` | ✅ | 返回 JD 解析结果 |

---

## 四、发现的问题

> 经二次核查：README 实际写的就是 `/ping`，并不存在 P1 文档不一致问题。下面只保留真实发现。

### 🟡 P3 — i18n 小瑕疵

**`apps/backend/app.py:245` 发送英文进度消息**

```python
yield sse({"status": "analyzing", "message": "Running analysis with LLM..."})
```

- 影响：在中文 UI 的"正在优化"流程中，下方进度条显示英文 "Running analysis with LLM..."，与"准备开始..."等中文反馈不一致
- 建议：改为 `"message": "正在调用大模型分析..."` 或类似中文

### 🟢 P5 — 移动端标题排版

**窄屏（< 420px）下 hero 副标题与主标题垂直间距偏紧**

- 影响：375px iPhone SE 等小屏可见文字"挤"在一起
- 建议：hero 组件给标题与副标题加 `mt-6` 或更大间距，或在 `md:mt-12` 改 `mt-8`

### 🟢 P5 — LLM 延迟可观

| 阶段 | 实测耗时 |
| --- | --- |
| JD 解析（`/jobs/upload`） | ~20s |
| 简历分析（`/improve?stream=true`） | ~50s |
| 深度重审（点"优化简历"） | ~55s |

- 影响：UX 等待时间长，需要进度反馈（已有）和乐观提示
- 建议：进度反馈已有，但可加一个"预计 30~60 秒"的文案

---

## 五、未测试 / 不测试项

- ❌ **a4cv 可视化编辑器**：用户明确说"不需要测试 a4cv，这是完全完美的"
- ❌ **多简历并发上传**：测试单份即可
- ❌ **nginx 反代 / HTTPS**：纯前端测试不覆盖
- ❌ **Docker 部署链路**：本地 dev 启动，不验证容器

---

## 六、清理

E2E 过程中临时添加到 `apps/frontend/public/` 的 `_e2e_resume.docx` / `_e2e_jd.txt` / `_e2e_bad.txt` 已在测试结束后删除。

后端 `data/storage/` 下产生了 2 个测试用的 resume/job 记录，可手动清理：

```bash
# 列出所有
ls apps/backend/data/storage/resumes/
ls apps/backend/data/storage/jobs/
# 删除测试数据
rm apps/backend/data/storage/resumes/6cc282db-acf5-46cc-b22b-654bf2c7ab5f.json
rm apps/backend/data/storage/resumes/57b9c529-11a3-4c6b-bdfb-f24b86356984.json
rm apps/backend/data/storage/jobs/<job-id-1>.json
rm apps/backend/data/storage/jobs/<job-id-2>.json
```

---

## 七、结论

✅ **核心端到端流程全部通过**，用户可正常完成"上传简历 → 粘贴 JD → 流式分析 → dashboard → 深度重审"完整链路。

🐛 **2 处可改进**（README 经二次核查无问题，已撤下 P1 项）：
1. 后端 SSE 进度消息汉化（`app.py:245`）
2. hero 在 < 420px 屏下加垂直间距

🔧 **建议优先级**：P3（i18n）→ P5（UI 间距）→ 可选：加载页加"预计 30~60 秒"提示

