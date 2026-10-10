# 设计与需求追踪

## 问题与设计选择

文档问答流程同时存在不确定的模型判断与必须确定执行的软件规则。Actor 决定读取什么证据，Reviewer 检查答案；是否允许结束、是否重试、是否写入记忆则交由显式程序规则。采用两个主要智能体可以保持角色分工和成本可观察，而无需将每个辅助组件都包装成智能体。

原 DocAgent 的树形导航、Reviewer、反思和工具调用轮数控制属于原有工作。本项目的研究性改动是：把引用合法性设为状态转换的守卫条件；把记忆来源、范围和使用前复核设为明确契约。事件队列和 MCP 则主要是工程改进，应与质量改进分开评价。

## 软件契约

`Answer = {answer, status, evidence[]}`，其中 status 为 `answered` 或 `insufficient`。每条 `Evidence` 包含 `id, doc_id, page, section_id, text, source_type`。页码从 1 开始。

Reviewer 返回 `verdict, answer, reason, memory_candidate`。`reason` 是短的审查结论，不要求或记录隐藏推理过程。`memory_candidate` 是尚待应用核验的候选经验。

`DocumentStore` 提供同一套工具语义，`LocalGateway` 与 `MCPGateway` 只改变调用边界。MCP 服务端使用官方 SDK、JSON Schema 工具声明、文本与图像内容块；客户端实际启动独立服务进程，执行初始化、工具发现和调用。文档范围只读，不把模型密钥传给工具子进程。

## 事件与状态

EventBus 以 FIFO 队列分发 `task_submitted / actor_completed / review_completed / validation_completed`。监听回调仅推进状态并调度 worker；耗时模型/工具操作不在分发回调内阻塞执行。事件 ID 去重只在当前进程和任务生命周期内有效。

优化模式的正常状态序列为 `pending → acting → reviewing → validating → completed`。校验失败或 Reviewer 要求修订时，在预算内回到 `acting`。全部活跃状态可到 `failed` 或 `cancelled`，终态不可重新激活。修订预算耗尽且引文仍不合法时，输出可辨认的“无法确认”，不是伪造一个答案。

Python 的监听接口是对 Java ActionListener 思想的应用，并非导入 `java.awt.event.ActionListener`。配套 Java 小例子才是真实 Java 接口，用后台 Executor 示范“监听回调”和“执行策略”的区别。

## 证据守卫的精确范围

对每条引用，根据 source_type 调用对应工具，从原始文档重新取证。校验文档、元素 ID、页码、类型一致，且 text 是源文本的非空连续片段。调用结果采用深拷贝，避免角色修改缓存后的“源证据”。

这能阻止不存在的页码、错误文档、改写引文和无出处肯定回答，却不能证明答案与证据在逻辑上相符。表图的确定性检查只验证源身份和标题/文本记录，像素含义仍由视觉模型解释。故障实验特意保留一个“真实引用配错误结论”的反例。

## 工具与记忆控制

GuardedGateway 对每个底层尝试计预算；缓存命中不算底层调用。相同只读请求在同一次任务中合并；独立请求可并发。参数错误不盲目重试，超时/暂时性故障在限额内重试。取消会终止当前 worker 和待完成工具任务。

MemoryStore 以文档 ID 隔离经验，内容去重并保存来源、证据、版本和时间。优化版只读取有来源验证标记的记录，并再次检查其证据是否仍有效。只有发生有证据支持的修正、任务最终成功且未冻结时才允许写入。测试集每题使用空且冻结的独立记忆，无法从前一道测试题学习答案。

当前版本不提供多人并发写同一个记忆文件的跨进程事务，也不提供持久消息队列或模型训练功能。

## 需求到实现与验证

| 需求 | UML | 实现 | 关键验证 |
| --- | --- | --- | --- |
| 角色协作 | 组件、活动、类 | LLMAgents / WorkflowEngine | Actor先于Reviewer；取消不触发后续角色 |
| 事件监听 | 状态、活动 | EventBus / Event | 队列实际驱动；重复事件不重复执行 |
| MCP调用 | 时序、组件 | MCPGateway / mcp_server | 真实stdio协商、六工具、图像字节往返 |
| 引用来源可靠 | 状态、类 | EvidenceGate | 伪页码、跨文档、改写引文拒绝 |
| 记忆治理 | 类、活动 | MemoryStore | 冻结、去重、旧来源失效、污染候选拒绝 |
| 可控故障 | 状态 | GuardedGateway | 有限重试、调用预算、超时、取消 |
| 可解释评价 | 用例 | evaluation / robustness | 规则评分边界、拒答不计作答对、消融 |
| 长文档工具能力 | 组件 | import_pdf / DocumentStore | 120页导入，第7/113页搜索和第120页渲染 |

完整测试名位于 `tests/`。UML 是实现的设计说明，图中省略的异常边在源状态迁移表中有显式定义。
