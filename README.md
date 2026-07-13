# 动车检修问题理解与处理建议系统

项目三的可集成骨架：支持纯规则、LLM 和混合模式；输出统一 JSON；LLM 不可用时自动回退到规则模式。

## 快速启动

```powershell
cd project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py "轴箱有点响，应该怎么办？"
streamlit run app.py
```

评估基线：

```powershell
python evaluation/evaluate.py rules
```

基础接口测试（无需 API）：

```powershell
python -m pytest tests -q
```

## 可选 LLM 配置

复制 `.env.example` 为 `.env`，填写 OpenAI-compatible API 的密钥、地址和模型名。无 `.env` 时，`llm` 和 `hybrid` 请求都会安全回退到规则模式。

## 团队约定

完整接口、分工和提交规范见 [docs/TEAM_PROTOCOL.md](docs/TEAM_PROTOCOL.md)。

## 组长首次发布

在实际远程仓库创建完成后，执行 `git init`、首次提交并推送；把 `docs/TEAM_PROTOCOL.md` 和本 README 发到群里。远程地址、成员权限和群公告需要由组长在学校指定的平台完成。
