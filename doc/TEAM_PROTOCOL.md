# 项目三协作协议

## 范围与类型

范围以给定规程节选及术语来源表为准，覆盖轮对、轴箱、悬挂、传动、制动和试验等内容。问题类型为：标准限度问题、故障诊断问题、工艺流程问题、超限处置问题、条件判断问题、部件信息问题、概念解释问题、非动车检修问题。

## 唯一接口

- `core.analyzer.analyze_with_rules(question) -> dict`：3 号维护。
- `core.llm_client.analyze_with_llm(question) -> (dict, float)`：1 号维护。
- `main.analyze(question, mode) -> dict`：唯一公共入口；4 号和 5 号只能调用此函数。
- `data/terminology.json`、`data/questions.json`：2 号按既有字段维护，变更格式必须先通知 1 号。

统一 JSON 的问题类型为8类，实体字段为部件、故障或现象、工艺、指标、数值、单位；路由标签为 `RAG`、`KG`、`CLARIFY`、`OUT_OF_SCOPE`。所有模式都必须返回相同字段；5号评估和4号前端通过main.analyze调用分析流程。接口含义见docs/接口与标注规范.md。

项目三要求输出处理建议的标签和理由，不要求执行RAG检索、图谱查询或生成维修答案。LLM负责分类和提取，完整性、澄清提示和路由使用共用规则；这些指标不应宣传为独立LLM决策效果。

术语词典每个别名必须能映射到一个标准词；2 号新增词条时需保留 PDF 页码或章节来源。样本的期望类型、缺失信息与处理标签必须使用本协议的固定枚举。

## 集成与安全

- 所有人从分支提交；1 号每日傍晚合并到主分支并运行 `python main.py` 与 `python evaluation/evaluate.py rules`。
- API 密钥只放 `.env`，从 `.env.example` 复制生成；禁止提交到 Git、报告或截图。
- API 失败必须回退规则模式，不能阻断演示。

## 每日交付

每日结束前提交一个可运行版本，并在群内说明：交付文件、验证方式、已知问题、明日优先级。
