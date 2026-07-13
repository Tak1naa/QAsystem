# 项目三协作协议

## 范围与类型

范围限定为规程中的轮对、轴箱和一系悬挂。问题类型固定为：标准限度问题、故障诊断问题、工艺流程问题、超限处置问题、非动车检修问题。

## 唯一接口

- `core.analyzer.analyze_with_rules(question) -> dict`：3 号维护。
- `core.llm_client.analyze_with_llm(question) -> (dict, float)`：1 号维护。
- `main.analyze(question, mode) -> dict`：唯一公共入口；4 号和 5 号只能调用此函数。
- `data/terminology.json`、`data/questions.json`：2 号按既有字段维护，变更格式必须先通知 1 号。

## 集成与安全

- 所有人从分支提交；1 号每日傍晚合并到主分支并运行 `python main.py` 与 `python evaluation/evaluate.py rules`。
- API 密钥只放 `.env`，从 `.env.example` 复制生成；禁止提交到 Git、报告或截图。
- API 失败必须回退规则模式，不能阻断演示。

## 每日交付

每日结束前提交一个可运行版本，并在群内说明：交付文件、验证方式、已知问题、明日优先级。

