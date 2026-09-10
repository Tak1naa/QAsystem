# 动车检修问题理解与处理建议系统

《铁路信息技术专业实践》项目三。使用Python识别8类问题、提取6类实体并归一化，判断缺失信息，输出RAG、KG、CLARIFY或OUT_OF_SCOPE标签和理由。

系统提供Streamlit页面、命令行和批量评估，统一调用 `main.analyze(question, mode)`。当前不执行RAG文档检索、知识图谱查询或维修答案生成。“信息完整”表示足以构造查询，不代表足以现场确诊。

## 安装与运行

解压后进入QAsystem目录。以下命令适用于Windows PowerShell；其他平台可用本机Python及对应虚拟环境路径。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe main.py --mode rules --question '轴箱有点响，可能是哪的问题？'
.\.venv\Scripts\python.exe -m streamlit run app.py
```

页面演示选择“纯规则”，无需API密钥或网络连接。依赖安装完成后即可离线分析。词典、来源记录和样本随源码提供。

## 离线测试与评估

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe evaluation/evaluate.py rules --samples data/questions.json --output evaluation/local_development
.\.venv\Scripts\python.exe evaluation/evaluate.py rules --samples data/questions_regression.json --output evaluation/local_regression
```

`tests/`是可复现的自动测试代码，必须保留。新评估写入local目录，避免覆盖下列固定证据。

| 固定证据 | 用途 |
|---|---|
| evaluation/baseline/original_rules.json | 修改前开发题与原始预测 |
| evaluation/development_comparison.json | 统一标注重评39题，问句变化的Q018不参与比较 |
| evaluation/holdout_first/ | 首次24题预测及逐题表，保留原始表现 |
| evaluation/recheck_20260909/development/ | 报告引用的40题规则复测，平均约0.69ms |
| evaluation/recheck_20260909/regression/ | 报告引用的24题规则回归，平均约0.84ms |
| evaluation/acceptance_20260909/ui_checks.json | 先前独立记录的页面交互检查，并非recheck批测耗时 |
| evaluation/offline_modes/ | 历史离线三模式回退实验，不能作为在线模型质量比较 |

首次24题分类23/24、实体完全匹配20/24、micro F1=0.94；修复与标注复核后的回归为24/24、F1=1.00。开发40题只有部分实体标注，其满分表示预期覆盖等当前指标，不是完整实体精确率。回归题已经参与开发，不能宣称未知问句100%准确率。耗时是固定记录的本机当次测量，不是性能保证。

## 三种模式与可选模型

- `rules`：只返回规则结果。
- `hybrid`：先算规则，置信度低于0.65才尝试模型。信息不足不是直接触发条件。
- `llm`：先算规则再尝试模型；失败时返回规则并标记来源。

CLI默认模式是hybrid，离线检查请像上面的命令一样显式指定rules。模型输出经过校验和术语归一化，完整性与路由仍复用规则。受处理的网络或格式异常最多尝试两次后回退；无密钥时直接回退。

如需在线功能，将 `.env.example` 复制为 `.env`，自行填写DEEPSEEK_API_KEY；其他配置为DEEPSEEK_BASE_URL、DEEPSEEK_MODEL、LLM_TIMEOUT_SECONDS。`.env`不随源码交付，也不能提交。现有文档记录曾完成DeepSeek单题连通检查，未完成当前版本在线批量质量比较。在线分析会发送问句和术语词典，纯规则无需此配置。

## 文件说明

- `main.py`、`app.py`、`config.py`：公共入口、页面、配置。
- `core/`：提取、分类、完整性、路由、接口校验和模型接入。
- `data/`：词典、来源记录、题集和标注修订。
- `evaluation/`、`tests/`：评估代码、固定结果和自动测试。
- `doc/`：课程资料、检修规程及协作约定。
- `docs/`：接口、术语来源、错误分析、验收与交付说明。

详细说明见[接口与标注规范](docs/接口与标注规范.md)、[错误分析与改进](docs/错误分析与改进.md)、[验收记录](docs/项目三逐项验收.md)、[源码交付说明](docs/源码交付说明.md)。报告与PPT是单独交付的材料，不放入源码压缩包。
