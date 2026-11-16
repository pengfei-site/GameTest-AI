# GameTest AI V0.1 项目建设说明
**项目名称：** GameTest AI  
**项目代号：** GTAI-001  
**文档版本：** V1.0  
**项目阶段：** V0.1 基础能力建设  
**开发环境：** Windows + Python 3.12  
**项目路径：** `D:\GameTest-AI`  
**当前进度：** STEP 01～06.4 已完成并验收，STEP 07 数据管理设计已完成核心规则确认。

---

# 一、项目概述

## 1.1 项目背景

在传统游戏测试工作中，测试人员需要阅读大量策划文档，理解复杂业务规则，并根据需求设计测试点和测试用例。

这一过程存在一些典型问题：

1.  策划文档内容复杂，人工拆解业务规则容易遗漏。
2.  测试点设计依赖测试人员的经验，质量和覆盖程度容易出现差异。
3.  数值、状态、异常场景需要大量人工推理。
4.  测试用例编写重复性较高，耗费大量时间。
5.  AI 生成内容可能出现业务规则理解错误、需求外推断、重复测试点等问题。
6.  AI 生成结果缺少系统化的校验和审核机制。

因此，本项目希望将 AI 能力引入游戏测试前期设计流程，建立一个能够辅助测试人员完成需求分析、测试点拆解和测试用例生成的工具。

## 1.2 项目目标

GameTest AI 的核心目标：

**将游戏策划文档转化为结构化需求、可追溯测试点和标准化测试用例。**

预期工作流程：

策划文档上传  
↓  
文档内容解析  
↓  
AI 结构化需求分析  
↓  
AI 测试点生成  
↓  
Python 确定性校验  
↓  
AI Reviewer 逻辑审查  
↓  
人工审核与修改  
↓  
测试用例生成  
↓  
Excel 导出

## 1.3 核心设计理念

AI 不是替代测试人员，而是测试效能的智能外脑。

系统采用 AI + Python + 人工审核的组合方式：

| 组成 | 主要职责 |
| --- | --- |
| AI | 需求理解、业务规则提取、测试点生成、逻辑审查 |
| Python | 数据结构校验、规则引用检查、编号检查、确定性检查 |
| 人工 | 业务判断、测试策略调整、最终审核和质量把关 |

核心原则：

*   AI 负责提高分析和生成效率。
*   Python 负责可确定的规则检查。
*   人工测试人员拥有最终决定权。
*   AI 不得擅自补充策划未明确的业务规则。
*   测试点必须能够追溯到原始需求。

---

# 二、V0.1 功能范围

## 2.1 计划实现功能

| 功能模块 | 功能说明 |
| --- | --- |
| 游戏项目管理 | 创建和管理游戏项目 |
| 策划文档管理 | 上传 Word、PDF、Markdown |
| 文档解析 | 提取段落、表格和文本 |
| AI 需求分析 | 提取业务规则和约束 |
| AI 测试点生成 | 按业务规则拆解测试点 |
| Python Validator | 确定性数据和规则检查 |
| AI Reviewer | 独立审查测试点逻辑 |
| 人工审核 | 编辑、通过、驳回测试点 |
| 测试用例生成 | 根据测试点生成标准化用例 |
| Excel 导出 | 导出审核后的测试用例 |
| 数据管理 | 保存项目、文档、分析、批次和测试点 |
| 历史记录 | 保留人工操作历史 |
| 数据备份 | 自动备份、手动备份和恢复 |

## 2.2 暂不纳入 V0.1 的功能

*   自动化测试执行。
*   缺陷管理。
*   多用户协作。
*   团队权限管理。
*   跨批次测试点自动合并。
*   服务端数据库部署。
*   知识库和历史项目经验复用。

知识库及更复杂的 AI 工作流计划放在 V0.2。

---

# 三、技术架构

## 3.1 技术选型

| 技术 | 用途 |
| --- | --- |
| Python 3.12 | 主要开发语言 |
| Streamlit | Web UI |
| DeepSeek API | AI 模型服务 |
| OpenAI SDK | 调用 OpenAI-compatible API |
| Pydantic | 结构化数据模型与校验 |
| SQLite | 本地数据存储 |
| python-docx | Word 文档解析 |
| PyMuPDF | PDF 文档解析 |
| openpyxl | Excel 导出 |
| pandas | 数据处理 |
| python-dotenv | 环境变量管理 |

## 3.2 系统结构

整体采用分层设计：

**表现层**

Streamlit 页面负责用户交互、文档上传、结果展示、人工审核和导出。

**业务逻辑层**

负责需求分析、测试点生成、测试点审查和后续测试用例生成。

**数据模型层**

使用 Pydantic 定义需求分析、测试点、审查结果等结构。

**AI 接入层**

统一封装 DeepSeek API 调用，处理 JSON 输出和模型响应。

**数据持久化层**

使用 SQLite 保存项目、文档、分析结果、生成批次、测试点和历史记录。

## 3.3 当前项目目录

目前已建立的主要文件：

```
D:\GameTest-AI
│
├── app.py
├── .env
├── .env.example
├── .gitignore
│
├── config
│   └── settings.py
│
├── core
│   ├── ai_client.py
│   ├── document_parser.py
│   ├── schemas.py
│   ├── requirement_analyzer.py
│   ├── testpoint_generator.py
│   ├── testpoint_validator.py
│   ├── review_schemas.py
│   ├── testpoint_reviewer.py
│   └── generation_schemas.py
│
├── pages
│   ├── 03_结构化需求分析.py
│   └── 其他已有页面
│
├── tests
│   └── 后续测试文件规划
│
└── .venv
```

说明：

以上为核心模块结构示意，实际文件以当前项目目录为准。后续增加数据库模块时，先检查已有文件，避免覆盖现有代码。

---

# 四、开发过程及阶段成果

## STEP 01：开发环境初始化

**状态：已完成并验收**

### 目标

建立 Python 开发环境，安装项目依赖，保证项目可以正常运行。

### 环境信息

*   操作系统：Windows
*   Python：3.12
*   项目路径：`D:\GameTest-AI`
*   虚拟环境：`.venv`

### 安装依赖

```
.\.venv\Scripts\python.exe -m pip install streamlit openai python-docx pymupdf openpyxl pandas pydantic python-dotenv
```

### 环境验证

```
.\.venv\Scripts\python.exe -c "import streamlit, openai, docx, fitz, openpyxl, pandas, pydantic, dotenv; print('GameTest AI dependencies: OK')"
```

预期结果：

```
GameTest AI dependencies: OK
```

### 遇到的问题

Windows PowerShell 执行虚拟环境 Activate.ps1 时遇到 ExecutionPolicy 权限限制。

解决方式：

不修改系统执行策略，直接调用虚拟环境 Python：

```
.\.venv\Scripts\python.exe
```

后续项目运行统一采用该方式。

### 安全要求

*   API Key 放在 `.env`。
*   `.env` 不提交到 Git。
*   `.venv/` 和缓存文件加入 `.gitignore`。
*   不在聊天记录、代码或日志中公开 API Key。

---

## STEP 02：Streamlit 首页搭建

**状态：已完成并验收**

### 目标

建立 GameTest AI 的 Web 操作入口。

### 实现内容

*   Streamlit 首页。
*   项目名称和功能介绍。
*   基础指标展示。
*   文件上传入口。
*   后续功能模块导航基础。

### 启动命令

```
.\.venv\Scripts\python.exe -m streamlit run app.py
```

访问地址：

```
http://localhost:8501
```

### 验收结果

*   Streamlit 正常启动。
*   浏览器可以访问首页。
*   页面能够正常展示。
*   基础文件上传交互正常。

---

## STEP 03：策划文档解析引擎

**状态：已完成并验收**

### 目标

支持游戏策划文档上传和文本提取，为后续 AI 分析提供输入。

### 文件位置

```
core\document_parser.py
```

### 支持格式

| 文件格式 | 解析方式 |
| --- | --- |
| DOCX | python-docx |
| PDF | PyMuPDF |
| Markdown | UTF-8-SIG / GB18030 |

### 解析能力

**DOCX**

*   提取段落文本。
*   提取表格内容。

**PDF**

*   提取文本。
*   获取页数。
*   统计字符数量。

**Markdown**

*   支持常见编码读取。
*   提取原始文本内容。

### 核心函数

```
parse_document(file_name, file_bytes)
```

返回结构：

```
{
    "content": "...",
    "file_type": "...",
    "page_count": 0,
    "char_count": 0
}
```

### 验收结果

*   支持文件上传。
*   能够解析支持格式的文档。
*   页面可以展示解析结果。
*   能够显示文档类型、页数和字符数量。

### 当前限制

扫描版 PDF 尚未接入 OCR。

如果 PDF 只有图片，没有可提取的文本，后续需要增加 OCR 能力。

---

## STEP 04：DeepSeek API 接入

**状态：已完成并验收**

### 目标

接入 DeepSeek 模型，使系统具备 AI 需求分析和测试点生成能力。

### 配置文件

```
.env
.env.example
config\settings.py
core\ai_client.py
```

### API 接入方式

使用 OpenAI SDK 的兼容接口方式调用 DeepSeek。

API Key 和模型配置通过环境变量读取。

### 核心能力

*   读取 API 配置。
*   创建 AI 客户端。
*   发送模型请求。
*   获取模型响应。
*   支持结构化 JSON 响应。

### 安全要求

API Key 不允许硬编码在 Python 文件中。

`.env.example` 只保存配置项示例，不包含真实密钥。

### 验收结果

*   DeepSeek API 连接成功。
*   模型可以正常返回结果。
*   Streamlit AI 需求分析体验页面运行正常。

---

## STEP 05：结构化需求分析

**状态：已完成并验收**

### 目标

将自然语言策划文档转换为结构化业务需求。

### 核心文件

```
core\schemas.py
core\requirement_analyzer.py
pages\03_结构化需求分析.py
```

### 需求分析结构

使用 Pydantic 定义：

*   BusinessRule
*   NumericConstraint
*   RequirementAnalysis

### 需求分析字段

| 字段 | 说明 |
| --- | --- |
| module | 功能模块 |
| summary | 需求摘要 |
| business\_rules | 业务规则 |
| preconditions | 前置条件 |
| states | 业务状态 |
| numeric\_constraints | 数值约束 |
| exception\_cases | 异常场景 |
| open\_questions | 待确认问题 |

### 业务规则结构

每条 BusinessRule 包含：

*   rule\_id
*   rule\_text
*   source\_text
*   status

其中 status：

*   confirmed
*   needs\_confirmation

### 数值约束结构

每条 NumericConstraint 包含：

*   name
*   value
*   unit
*   description

### AI 工作流程

1.  输入策划文档文本。
2.  调用 DeepSeek。
3.  要求模型输出结构化 JSON。
4.  使用 Pydantic 校验数据。
5.  返回结构化需求分析结果。

### 页面展示

*   需求摘要。
*   业务规则。
*   前置条件。
*   业务状态。
*   数值约束。
*   异常场景。
*   待确认问题。
*   完整 JSON。
*   JSON 下载。

### 曾遇到的问题

DeepSeek 输出的 numeric\_constraints 字段曾出现结构不一致问题。

处理原则：

先检查模型真实返回的 JSON，再确定是否需要调整 schema，不盲目修改数据模型。

### 验收结果

结构化需求分析页面运行正常，能够展示和下载结构化结果。

---

## STEP 06：AI 测试点生成与逻辑审查

STEP 06 是目前项目中最重要的 AI 业务能力建设阶段。

拆分为：

*   STEP 06.1 测试点数据模型。
*   STEP 06.2 AI 测试点生成引擎。
*   STEP 06.3 AI Reviewer 逻辑审查。
*   STEP 06.4 Reviewer 接入测试点生成流程。

### STEP 06.1：测试点数据模型

**状态：已完成并验收**

核心文件：

```
core\schemas.py
```

TestPoint 数据模型：

```
class TestPoint(BaseModel):
    point_id: str
    requirement_id: str
    category: Literal[
        "positive",
        "negative",
        "boundary",
        "exception",
        "state",
        "data"
    ]
    title: str
    test_objective: str
    coverage_description: str
    priority: Literal[
        "P0",
        "P1",
        "P2",
        "P3"
    ]
    source_rule: str
```

测试点集合：

```
class TestPointCollection(BaseModel):
    module: str
    points: list[TestPoint] = Field(default_factory=list)
```

### 测试点分类

| 分类 | 说明 |
| --- | --- |
| positive | 正向测试 |
| negative | 反向测试 |
| boundary | 边界测试 |
| exception | 异常测试 |
| state | 状态测试 |
| data | 数据测试 |

优先级：

*   P0
*   P1
*   P2
*   P3

测试点必须关联需求规则，并保留对应来源规则文本。

---

### STEP 06.2：AI 测试点生成引擎

**状态：已完成基础能力，质量规则持续优化**

核心文件：

```
core\testpoint_generator.py
core\testpoint_validator.py
```

核心函数：

```
generate_testpoints(
    requirement: RequirementAnalysis
)
```

### 生成目标

基于结构化需求分析，自动拆解测试点。

AI 需要关注：

*   正向场景。
*   反向场景。
*   边界场景。
*   异常场景。
*   状态场景。
*   数据场景。

### 生成约束

目前已经建立较完整的 Prompt 规则，核心要求如下：

1.  只基于 business\_rules 生成测试点。
2.  requirement\_id 必须引用真实存在的规则编号。
3.  source\_rule 必须与对应 rule\_text 完全一致。
4.  一个测试点只允许有一个主要关联规则。
5.  不得擅自增加需求外的测试场景。
6.  不得将待确认规则写成确定预期。
7.  避免重复测试点。
8.  每个测试点必须有独立测试目的。
9.  数值运算必须正确。
10.  区分数值增加和数值上限。
11.  不擅自补充策划未定义的 UI 行为。
12.  跨天重置时间未明确时必须标记待确认。

### Python Validator

为减少 AI Prompt 的无限扩张，系统引入 Python 确定性校验。

Validator 主要负责：

*   测试点结构检查。
*   必填字段检查。
*   测试点编号检查。
*   需求规则引用检查。
*   source\_rule 原文一致性检查。
*   重复和相似测试点提示。
*   参数化测试候选提示。

### 验收结果

真实 AI 生成运行成功。

曾有一次测试生成 11 个测试点：

*   errors：0
*   warnings：3

随后针对相似度启发式检查进行了优化。

当前原则：

AI 负责理解和生成，Python 负责能够明确判断的规则，不将模糊业务判断强行写成程序规则。

---

### STEP 06.3：AI Reviewer 逻辑审查

**状态：已完成并验收**

核心文件：

```
core\review_schemas.py
core\testpoint_reviewer.py
```

### 设计目标

让另一个独立 AI 审查测试点生成结果。

Reviewer 不直接修改测试点，而是返回问题和审核建议。

### 审查问题类型

| issue\_type | 说明 |
| --- | --- |
| logic\_error | 逻辑错误 |
| unsupported\_inference | 无依据推断 |
| unclear\_expectation | 预期结果不明确 |
| coverage\_overlap | 覆盖重复 |
| missing\_coverage | 覆盖缺失 |
| requirement\_conflict | 与需求冲突 |

严重程度：

*   critical
*   major
*   minor

### Reviewer 输出结构

```
class TestPointReviewResult(BaseModel):
    overall_status: Literal[
        "passed",
        "needs_review",
        "failed"
    ]

    summary: str

    issues: list[TestPointIssue] = Field(
        default_factory=list
    )

    approved_point_ids: list[str] = Field(
        default_factory=list
    )

    review_point_ids: list[str] = Field(
        default_factory=list
    )
```

### 中文 JSON 兼容

DeepSeek 可能返回中文字段，因此 Reviewer 增加标准化处理。

字段映射：

| 中文字段 | 标准字段 |
| --- | --- |
| 审查状态 | overall\_status |
| 通过测试点 | approved\_point\_ids |
| 复核测试点 | review\_point\_ids |
| 问题列表 | issues |
| 测试点编号 | point\_id |
| 问题类型 | issue\_type |
| 问题描述 | description |
| 问题建议 | suggestion |

同时兼容部分英文别名。

### Reviewer 数据校验

1.  所有测试点编号必须合法。
2.  问题涉及的测试点必须进入复核列表。
3.  未分类的测试点默认进入复核列表。
4.  不能因为 AI 没有提及某条测试点就默认通过。
5.  AI Reviewer 不得修改测试点原始数据。

### 数值推理专项优化

针对数值逻辑，增加以下约束：

*   必须执行数值计算。
*   50 + 20 = 70，若上限为 100，则不触发溢出。
*   只有超过上限时，才需要检查溢出规则。
*   区分领取资格明确和最终数值处理未明确。
*   一个测试点包含多个验证目标时，不能因为其中一部分待确认，就否定已经有明确依据的部分。

### 验收案例

使用每日体力领取功能进行 Reviewer 测试。

需求规则涉及：

*   每天免费领取一次。
*   领取成功增加 20 点体力。
*   体力上限为 100。
*   当前体力不足 100 时允许领取。
*   成功领取后当日不能再次领取。

重点检查：

| 测试点 | 主要问题 |
| --- | --- |
| TP003 | 当前 99，领取增加 20，最终溢出处理未明确 |
| TP004 | 当前体力 100 时是否允许领取未明确 |
| TP006 | 当前 90，领取增加 20，最终溢出处理未明确 |
| TP008 | 跨天重置时间未明确 |
| TP009 | 当前 50，增加 20，最终为 70，不触发上限 |
| TP010 | 当日重复领取，明确不允许 |

最终 Reviewer 输出：

*   overall\_status：needs\_review
*   approved\_point\_ids：TP009、TP010
*   review\_point\_ids：TP003、TP004、TP006、TP008

4 条待复核问题均为 unclear\_expectation，severity 为 minor。

验收结果：

*   中文字段映射正常。
*   数值推理结果符合预期。
*   测试点编号校验正常。
*   待复核和通过列表正确。

---

### STEP 06.4：AI Reviewer 接入测试点生成流程

**状态：已完成并验收**

### 设计目标

将测试点生成、Python Validator 和 AI Reviewer 整合成完整工作流。

### 完整执行流程

```
输入结构化需求
       │
       ▼
AI 生成测试点
       │
       ▼
Pydantic 数据校验
       │
       ▼
Python Validator
       │
       ├── 校验失败
       │      │
       │      ▼
       │   返回 validation_failed
       │   保留校验报告
       │   跳过 AI Reviewer
       │
       ▼
校验通过
       │
       ▼
AI Reviewer
       │
       ▼
统一生成结果
       │
       ▼
等待人工审核
```

### 统一结果模型

文件：

```
core\generation_schemas.py
```

包括：

*   ParameterizedCandidate
*   TestPointValidationReport
*   TestPointGenerationResult

最终结果模型：

```
class TestPointGenerationResult(BaseModel):
    testpoints: TestPointCollection
    validation_report: TestPointValidationReport
    review_report: TestPointReviewResult

    final_status: Literal[
        "ready_for_manual_review",
        "needs_manual_review",
        "review_failed",
        "validation_failed"
    ]
```

### 最终状态映射

| Python Validator | AI Reviewer | 最终状态 |
| --- | --- | --- |
| 通过 | passed | ready\_for\_manual\_review |
| 通过 | needs\_review | needs\_manual\_review |
| 通过 | failed | review\_failed |
| 失败 | 不执行 | validation\_failed |

### 核心设计原则

1.  AI 生成与 AI 审查分离。
2.  Reviewer 不直接修改测试点。
3.  Python Validator 和 AI Reviewer 报告分别保留。
4.  Python errors 阻断后续 AI Reviewer。
5.  Python warnings 不阻断流程。
6.  即使 AI Reviewer 通过，也只是进入人工审核。
7.  人工审核拥有最终决定权。

### 集成测试结果

使用每日体力领取需求进行完整集成测试。

测试结果：

*   Validator 检查测试点：10 条。
*   errors：0。
*   warnings：0。
*   AI Reviewer：needs\_review。
*   AI 审查通过：6 条。
*   AI 待复核：4 条。
*   最终状态：needs\_manual\_review。

最终流程正常运行。

### 当前注意事项

独立 Reviewer 测试与完整生成集成测试在测试日志中可能同时出现。

后续可以优化测试脚本组织，避免重复调用 API，但不影响当前完整流程验收结果。

---

# 五、当前核心业务工作流

截至 STEP 06.4，系统已经具备以下核心能力：

## 5.1 需求分析工作流

输入：

游戏策划文档文本。

处理：

1.  AI 理解需求。
2.  提取业务规则。
3.  提取前置条件。
4.  提取业务状态。
5.  提取数值约束。
6.  提取异常情况。
7.  标记待确认问题。
8.  Pydantic 校验结构。

输出：

RequirementAnalysis。

## 5.2 测试点生成工作流

输入：

RequirementAnalysis。

处理：

1.  AI 拆解测试点。
2.  生成六种测试类型。
3.  关联需求规则。
4.  校验数据结构。
5.  Python Validator 检查。
6.  AI Reviewer 独立审查。
7.  汇总最终结果。

输出：

TestPointGenerationResult。

## 5.3 当前能力边界

目前已经实现：

*   文档解析。
*   AI 需求分析。
*   AI 测试点生成。
*   Python 确定性校验。
*   AI Reviewer 逻辑审查。
*   生成结果统一封装。

尚未完成：

*   测试点持久化管理。
*   人工审核页面。
*   项目和文档版本管理。
*   测试用例生成。
*   Excel 完整导出工作流。
*   数据备份与恢复。

这些能力将在后续阶段逐步完成。

---

# 六、当前项目进度

| 阶段 | 开发内容 | 状态 |
| --- | --- | --- |
| STEP 01 | Python 环境初始化 | 已完成 |
| STEP 02 | Streamlit 首页 | 已完成 |
| STEP 03 | 文档解析引擎 | 已完成 |
| STEP 04 | DeepSeek API 接入 | 已完成 |
| STEP 05 | 结构化需求分析 | 已完成 |
| STEP 06.1 | 测试点数据模型 | 已完成 |
| STEP 06.2 | AI 测试点生成引擎 | 已完成 |
| STEP 06.3 | AI Reviewer 逻辑审查 | 已完成 |
| STEP 06.4 | Reviewer 流程集成 | 已完成 |
| STEP 07 | 数据管理设计 | 核心规则已确认 |
| STEP 08 | 人工审核与管理页面 | 待开发 |
| STEP 09 | 测试用例生成 | 待开发 |
| STEP 10 | Excel 导出 | 待开发 |
| STEP 11 | 整体流程验收与优化 | 待开发 |

说明：STEP 07 已确认的详细设计以《GameTest AI V0.1 数据管理设计说明》为准。

---

# 七、开发过程中的重要经验

## 7.1 不要无限扩展 Prompt

AI 生成质量不可能完全依赖 Prompt 解决。

对于可以明确判断的规则，应优先交给 Python Validator。

例如：

*   编号是否存在。
*   需求规则是否存在。
*   来源文本是否一致。
*   数据结构是否合法。

AI 更适合负责业务理解和复杂逻辑分析。

## 7.2 AI 生成和 AI 审查必须分离

生成模型可能重复自己的错误。

因此，生成和审查采用独立调用。

Reviewer 只返回问题，不直接修改生成结果。

## 7.3 未明确需求不能擅自补全

例如：

策划只写明体力上限为 100，并没有说明超过上限后的处理方式。

AI 不能擅自认定：

*   溢出体力被丢弃。
*   溢出体力保留。
*   不允许领取。
*   自动转化其他资源。

这些情况应标记为待确认。

## 7.4 数值测试必须进行实际计算

不能只根据关键词判断。

例如：

当前体力 50，领取增加 20，体力上限 100。

计算结果为 70，没有触发上限。

当前体力 90，领取增加 20，结果为 110，才涉及上限处理规则。

## 7.5 保留原始结果

后续数据管理中，AI 原始测试点与人工修改后的内容必须分离。

这样才能比较 AI 初稿和人工最终结果，也能为后续 AI 质量评估提供数据。

---

# 八、后续开发路线

## STEP 07：数据管理与数据库

依据独立的数据管理设计说明实施：

1.  检查现有项目和数据库。
2.  建立 SQLite 数据层。
3.  创建六张核心表。
4.  实现项目管理和文档版本管理。
5.  保存需求分析与生成批次。
6.  保存测试点及审核状态。
7.  实现历史记录。
8.  实现备份和恢复。

## STEP 08：测试点人工审核页面

实现：

*   批次列表。
*   测试点列表。
*   测试点详情。
*   人工编辑。
*   单条审核。
*   批量审核。
*   驳回原因。
*   逻辑删除和恢复。
*   操作历史查看。

## STEP 09：AI 测试用例生成

根据已审核测试点生成标准化测试用例。

计划字段：

*   case\_id
*   module
*   requirement\_id
*   test\_point
*   title
*   preconditions
*   steps
*   expected\_results
*   priority
*   test\_type
*   review\_status

要求：

测试用例必须能够追溯到对应测试点和需求规则。

## STEP 10：Excel 导出

支持：

*   当前批次全部有效测试点或测试用例导出。
*   仅导出人工审核通过的数据。
*   保留需求和批次追溯信息。

## STEP 11：完整流程验收

最终完整流程：

创建游戏项目  
→ 上传策划文档  
→ 文档解析  
→ AI 需求分析  
→ AI 测试点生成  
→ Python Validator  
→ AI Reviewer  
→ 人工审核  
→ AI 测试用例生成  
→ Excel 导出  
→ 数据归档和备份

---

# 九、项目阶段性总结

GameTest AI V0.1 已经完成最重要的 AI 核心能力验证：

1.  能够解析常见策划文档。
2.  能够将自然语言需求转换为结构化业务规则。
3.  能够基于业务规则生成测试点。
4.  能够使用 Python 对生成结果进行确定性校验。
5.  能够使用独立 AI Reviewer 审查测试点逻辑。
6.  能够统一保存生成、校验和审查结果。

当前项目从单纯的 AI 测试点生成脚本，已经逐步形成完整的游戏测试辅助工具架构。

接下来开发重点将从 AI 能力验证转向工程化：

*   数据持久化。
*   人工审核。
*   测试用例生成。
*   数据追溯。
*   Excel 交付。
*   稳定性和安全性。

**最终目标：建立一套能够真正融入游戏测试工作流程的 AI 辅助测试系统，而不仅仅是一个调用大模型生成测试点的演示工具。**