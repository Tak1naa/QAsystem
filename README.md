# 动车检修问题理解与处理建议系统

项目三的问题理解原型：支持8类问题、6类实体及纯规则、LLM和混合模式；输出统一JSON；LLM不可用时回退规则。项目验收状态见[逐项验收记录](docs/项目三逐项验收.md)。

## 快速启动

```powershell
cd QAsystem
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py "轴箱有点响，应该怎么办？"
streamlit run app.py
```

评估基线：

```powershell
python evaluation/evaluate.py rules
```

完整标注的24题规则验收：

```powershell
python evaluation/evaluate.py rules --samples data/questions_regression.json --output evaluation/latest_regression
```

在线批测需配置自己的DeepSeek密钥，`all`会产生API调用费用：

```powershell
python evaluation/evaluate.py all --samples data/questions_regression.json --output evaluation/online_run
```

完整标注题报告实体完全匹配和micro P/R/F1，40题开发集只有部分实体标注，报告预期实体覆盖。历史首次测试不得被回归结果覆盖。

基础接口测试（无需 API）：

```powershell
python -m pytest tests -q
```

## 可选 LLM 配置

复制 `.env.example` 为 `.env`，填写 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`；`.env` 已被 Git 忽略，不能提交、截图或写入报告。无密钥时，需要在线调用的请求会回退到规则模式。

当前输出的是问题理解和检索路由，尚未接入RAG文档检索或KG知识图谱执行模块，因此不会直接返回故障原因或维修答案。完整性表示信息足以构造检索，不表示足以现场确诊。

处理模式：

- `rules`：只运行离线规则，适合基线评估。
- `llm`：优先调用在线模型；调用失败自动回退规则模式。
- `hybrid`：先运行规则；低置信度问题才调用在线模型，适合页面演示。

常见问题：若提示“未配置 DEEPSEEK_API_KEY”，请检查 `.env` 是否与 `main.py` 同级；若 API 超时或返回格式不合法，系统会重试一次后回退规则模式，并在输出的 `元数据` 中标记原因。

## 团队约定

完整接口、分工和提交规范见 [doc/TEAM_PROTOCOL.md](doc/TEAM_PROTOCOL.md)。

## 组长首次发布

在实际远程仓库创建完成后，执行 `git init`、首次提交并推送；把 `docs/TEAM_PROTOCOL.md` 和本 README 发到群里。远程地址、成员权限和群公告需要由组长在学校指定的平台完成。
