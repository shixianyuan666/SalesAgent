# 技术文档：多平台智能售卖智能体（Vue + FastAPI + LangGraph）

本文档面向“产品交付后需要给研发/运维/甲方解释每个模块怎么写、用了什么技术、为什么用、带来什么好处”的场景。代码以 **Vue 3 + TypeScript**（运营台）和 **FastAPI + Python**（服务端）为主，智能体采用 **LangChain 生态 + LangGraph** 的“有状态图编排”。

## 1. 总览

### 1.1 目标

- 接入飞书等平台消息（MVP：飞书优先），统一进入系统
- 智能体不是“问答”，而是 **有目标、有状态、有工具调用的售卖流程**（A 澄清式 + D 长期记忆 + F 无缝转人工）
- 从商品库做 **关键词 + 向量检索的混合召回**，并加入“一致性校验”防止相似商品误发
- 运营台让小白能快速上手：商品上传 → 重建向量 → 收件箱接管 → 记忆查看/清除

### 1.2 目录结构

- 前端（Vue）
  - `src/pages/*`：页面
  - `src/components/*`：通用组件（壳/导航）
  - `src/lib/api.ts`：API 请求封装（含 token 处理）
  - `src/composables/useAuth.ts`：登录态
  - `vite.config.ts`：开发代理（/api /uploads /webhooks 转发到后端）
- 后端（FastAPI）
  - `api/main.py`：FastAPI 入口，路由注册，静态文件挂载
  - `api/core/*`：基础能力（DB、ID、鉴权）
  - `api/models.py`：Pydantic 模型（Product/Conversation/Message/Memory/Config）
  - `api/repos/*`：数据访问层（SQLite）
  - `api/routes/*`：HTTP API 路由层
  - `api/services/*`：领域服务（LLM/Embedding 兼容、检索、智能体服务）
  - `api/agent/*`：LangGraph 智能体图
  - `api/connectors/*`：平台连接器（MVP：飞书 + mock）

## 2. 技术选型与原因

### 2.1 为什么前端选 Vue 3 + TS + Vite + Tailwind

- Vue 3 组合式 API 对“表单多、列表多、状态多”的后台更友好，学习成本对小白更低
- TypeScript：减少接口字段/状态机类型错误；与后端接口对接更稳
- Vite：开发启动快、热更新快，适合快速迭代 MVP
- Tailwind：不引入重量 UI 框架的情况下，能快速做出一致的后台风格；减少写 CSS 的维护成本

### 2.2 为什么后端选 FastAPI + SQLite（可升级 PostgreSQL）

- FastAPI：异步友好、声明式参数校验、OpenAPI 文档自动生成，适合“Webhook + API 控制台”组合
- SQLite：MVP 依赖最小，易部署；数据模型稳定后可平滑升级 PostgreSQL

### 2.3 为什么智能体用 LangGraph（而不是简单问答 / 仅 AgentExecutor）

- 你要求“智能体而不是问答”，关键在于 **可控流程 + 状态**：
  - 澄清节点：缺信息就问，不乱推
  - 检索节点：明确工具调用
  - 校验节点：防误发（相似但不满足需求）
  - 记忆节点：长期偏好与摘要滚动
  - 转人工节点：低置信/敏感场景可控接管
- LangGraph 的好处是 **可解释、可测试、可扩展**：节点边界清晰，后续加“比价/优惠策略/库存检查/下单引导”不会把代码写成一坨 prompt

### 2.4 为什么 LLM/Embedding 采用“OpenAI 兼容接口模式 → 可切本地模型”

- 前期：用阿里云/豆包等托管模型接口，省掉部署与推理运维，快速验证产品
- 后期：成熟后可替换为本地模型（vLLM/Ollama/LM Studio），把成本与数据控制权收回
- 技术落地方式：对 LLM/Embedding 做统一抽象（`OpenAICompatClient`），业务代码只依赖抽象，不绑定某一家厂商

## 3. 后端模块详解（FastAPI）

### 3.1 入口与路由注册

- 入口：`api/main.py`
  - 初始化 DB（建表）
  - 挂载静态目录 `/uploads`（商品图片回显与回发）
  - 注册路由：
    - `/api/auth/*` 登录
    - `/api/products/*` 商品与图片
    - `/api/conversations/*` 收件箱会话/消息（人工接管入口）
    - `/api/settings/*` 连接器/LLM/智能体策略
    - `/api/memory/*` 长期记忆管理（查看/清除）
    - `/webhooks/*` 平台回调（mock/飞书）

### 3.2 数据层：SQLite + Repository

- DB 工具：`api/core/db.py`
  - `init_db()`：一次性建表（product/product_image/conversation/message/settings/user_memory/user_memory_event）
  - `get_conn()`：上下文管理连接，自动 commit/close
  - `json_dump/json_load`：把 tags/payload/preferences 等结构化字段落库为 JSON
- Repository 分层的原因：
  - 路由层只负责 HTTP；业务服务只关心“做什么”；repo 专注“怎么读写数据”
  - 测试更容易：服务层可用假 repo 替换

### 3.3 鉴权：简化 JWT（MVP）

- 实现：`api/core/auth.py`
  - `issue_token(sub)`：HMAC-SHA256 签名的轻量 token
  - `require_auth`：FastAPI dependency，从 `Authorization: Bearer` 中校验
- 为什么先用简化版：
  - MVP 只需要后台运营台保护，不引入复杂依赖
  - 后续可无缝替换为标准 JWT 库（接口不变）

### 3.4 商品模块（CRUD + 图片）

- 路由：`api/routes/products.py`
- Repo：`api/repos/product_repo.py`
- 关键点：
  - 图片上传：`multipart/form-data` 写入 `api/uploads`，并在 `product_image.url` 里存 `/uploads/<file>`
  - 商品 embedding：`product.embedding_json` 保存向量（list[float]）
  - `/api/products/reindex`：重建向量索引（MVP 做全量；后续可做增量）

### 3.5 会话与消息（收件箱）

- 路由：`api/routes/conversations.py`
- Repo：`api/repos/conversation_repo.py`
- 关键点：
  - `get_or_create(platform, external_conversation_id)`：平台会话映射到系统会话
  - message.payload 用 union（text / products），落库为 JSON
  - status：
    - `auto`：智能体自动回复
    - `needs_human`：智能体建议转人工（低置信/敏感词/用户要求）
    - `human`：运营人员已接管并手动发消息

### 3.6 设置模块（连接器 / 模型 / 智能体策略）

- 路由：`api/routes/settings.py`
- Repo：`api/repos/settings_repo.py`
- 安全策略：
  - GET connectors 时对 `access_token/app_secret` 做脱敏（返回 null）
  - PUT connectors 时如果 token/secret 留空，则不覆盖已有值（避免页面误操作清空凭证）
- LLM 配置：
  - `base_url/api_key/chat_model/embedding_model`
  - 支持 OpenAI 兼容服务：阿里云/豆包/其他厂商

### 3.7 长期记忆（永久保存 + 手动清除）

- 路由：`api/routes/memory.py`
- Repo：`api/repos/memory_repo.py`
- 数据结构：
  - `preferences_json`：结构化偏好（用途/预算/最近推荐等）
  - `summary_text`：滚动摘要（便于“更像真人”的连续对话）
  - `user_memory_event`：事件流（后续可做审计、画像、回放）
- 清除：`DELETE /api/memory/users/{user_id}` 硬删（符合“永久但可一键清除”的直觉）

## 4. 智能体（LangGraph）模块详解

### 4.1 为什么这套智能体“不是简单问答”

关键在于：它始终在执行一个“售卖任务”的流程，而不是单轮回答。

流程节点在 `api/agent/graph.py`：

1. `read_memory`：读取用户长期记忆（偏好 + 摘要）
2. `extract_slots`：抽取/更新关键槽位（用途 use_case、预算 budget），并处理“上轮追问”的续答
3. `rewrite_query`：把“本轮需求 + 记忆偏好”合并成检索 query
4. `retrieve`：混合召回（关键词 + 向量）
5. `judge`：一致性校验（有 LLM 则用 LLM 从候选中筛，避免误发；否则用阈值规则）
6. `compose`：生成“推荐话术 + 链接”或“继续澄清的问题”
7. `update_memory`：写回记忆与事件流，形成长期闭环

### 4.2 澄清式多轮（A）

- 当缺用途/预算时，`compose` 会输出明确问题，并把 `last_question/pending_need` 写入记忆
- 用户下一句回答会被 `extract_slots` 识别并与 `pending_need` 合并，避免“只回答了办公/5000元却丢了原始需求”的机器人感

### 4.3 混合检索（关键词 + 向量）

- 代码：`api/services/retrieval.py`
- 得分融合：`score = 0.55 * vector + 0.45 * keyword`
- 好处：
  - 纯关键词：容易漏召回（同义词/表达差异）
  - 纯向量：在小数据或 embedding 不稳定时可能飘
  - 融合：兼顾稳定性与语义召回

### 4.4 防误发：一致性校验（你提出的关键点）

在 `judge` 节点中：

- 若配置了 LLM（chat_model），会把 `user_need + candidates` 打包为 JSON，请 LLM 返回 `accepted_ids`
- 好处：
  - 对“看起来相似但不满足关键条件”的候选做二次过滤
  - 便于后续升级为更严谨的校验：例如“必须包含某规格/必须满足价格区间”

### 4.5 无缝转人工（F）

- 在 `extract_slots` 中对“转人工/投诉/退款/客服”等关键字做触发
- 输出 `need_human=true` 后，服务层会把会话状态置为 `needs_human`
- 运营台收件箱会明显标记并允许人工发消息/发商品

## 5. 平台连接器（飞书优先）

### 5.1 连接器接口

- 抽象：`api/connectors/base.py`
  - `send_text(chat_id, text)`
  - `send_products(chat_id, products, text)`（MVP：先发图片，再发文字+链接）

### 5.2 飞书实现

- `api/connectors/feishu_auth.py`
  - 使用 `app_id/app_secret` 自动获取 `tenant_access_token`，并在进程内缓存（避免每次调用都请求鉴权）
- `api/connectors/feishu.py`
  - `im/v1/images` 上传图片拿 `image_key`
  - `im/v1/messages` 发送 text/image
  - 发送商品时：先尝试把商品首图发出去，再发一段带链接的推荐话术

### 5.3 Webhook（飞书）

- `api/routes/webhooks.py`
  - 支持 `challenge` 校验
  - 可选校验 `verify_token`（推荐配置）
  - 解析文本消息并调用 `AgentService.handle_inbound`

## 6. 前端模块详解（Vue）

### 6.1 路由与登录保护

- `src/router/index.ts`
  - `meta.requiresAuth` 控制需要登录的页面
  - 全局守卫：未登录跳转 `/login`

### 6.2 API 封装与 token

- `src/lib/api.ts`
  - 自动注入 `Authorization: Bearer <token>`
  - 统一错误结构，页面直接显示 `err.message`

### 6.3 页面模块

- 登录：`src/pages/LoginPage.vue`
- 概览：`src/pages/DashboardPage.vue`（商品数/会话数快速确认系统是否在跑）
- 商品：`src/pages/ProductsPage.vue`
  - 新建/编辑商品
  - 多图上传
  - 一键“重建向量”
- 收件箱：`src/pages/InboxPage.vue`
  - 会话列表 + 消息时间轴
  - 手动发文本/手动发商品（运营接管）
- 设置：`src/pages/SettingsPage.vue`
  - 飞书连接器（token/app_id/app_secret/verify_token）
  - LLM/Embedding（OpenAI 兼容）
  - 智能体策略（TopN/阈值/兜底话术）
- 记忆：`src/pages/MemoryPage.vue`
  - 查看/搜索用户记忆
  - 一键清除

## 7. 部署与运行

### 7.1 本地开发

- 启动前端：`pnpm run client:dev`
- 启动后端：`pnpm run server:dev`
- 一键启动：`pnpm run dev`

Vite 已配置代理（`vite.config.ts`），开发时前端请求 `/api/*` 会转发到后端 `3001`。

### 7.2 生产部署建议（下一步）

- 后端：
  - 使用 `uvicorn` + 进程管理（systemd/docker/k8s）
  - SQLite 可先用卷挂载；正式可迁移 PostgreSQL
  - 上传文件建议切对象存储（OSS/S3），避免多实例本地盘不一致
- 前端：
  - `pnpm run build` 输出静态资源，部署到 Nginx / CDN

## 8. 扩展路线（按你的规划）

### 8.1 从“接口模型”切到“本地模型”

- 保持业务只依赖 `OpenAICompatClient`
- 把 `base_url` 指向你的本地推理服务（例如 vLLM/Ollama 的 OpenAI compatible endpoint）
- embedding 与 chat 可分别配置不同的模型

### 8.2 扩展钉钉 / WhatsApp

- 按 `PlatformConnector` 增加实现文件：
  - `api/connectors/dingtalk.py`
  - `api/connectors/whatsapp.py`
- 在 `api/connectors/registry.py` 注册并从 settings 读取配置
- webhook 解析在 `api/routes/webhooks.py` 增加对应入口，把平台 payload 标准化后调用 `AgentService.handle_inbound`

### 8.3 更“人性化”的智能体升级点

- 更细的槽位体系（品牌/尺寸/颜色/数量/交付时间）
- 更稳定的“对话摘要”策略（定期摘要，而不是简单拼接）
- 引入意图分类（咨询/对比/强意向/投诉）驱动不同话术与转人工策略
- 引入“运营可控提示词模板”与版本管理（便于 A/B 测试）

