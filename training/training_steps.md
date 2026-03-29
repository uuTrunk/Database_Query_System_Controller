# Training Steps (Controller)

## 1. 目标

本文档说明 Controller 项目中并发训练/预测模型的完整流程。

相关脚本已统一放在 `training/` 目录：
1. `training/gen_training_questions.py`
2. `training/test_ask_graph.py`
3. `training/model.py`
4. `training/predict.py`

---

## 2. 前置条件

1. Agent 服务已启动，且 `config/config.yaml` 中 `server.host`、`server.port` 可达。
2. MySQL 可访问，`config/config.yaml` 中数据库配置正确。
3. 依赖已安装：

```bash
pip install -r requirement.txt
```

---

## 3. 首次训练与上线流程

### 步骤 1：生成训练问题

```bash
python -m training.gen_training_questions
```

输出文件：
- `gened_questions/training_questions_for_graph.csv`

### 步骤 2：采样离线日志

```bash
python -m training.test_ask_graph
```

输出目录：
- `output_store/data_log/ask_graph_*.csv`
- `output_store/ask-graph/`（返回图片与详情）

### 步骤 3：训练并保存模型

```bash
python -m training.model
```

输出目录：
- `saves/model_best.pth`
- `saves/model_*.pth`
- `train_logs/log_*.csv`

### 步骤 4：启动在线界面（启用预测并发调度）

```bash
python main.py
```

在线逻辑：
1. `main.py` 调用 `training/predict.py` 预测单次成功率 $p$。
2. 根据 $1 - (1-p)^n \ge 0.99$ 计算最小并发线程数 $n$，并限制在 `[1, 5]`。
3. 使用 `ThreadPoolExecutor(max_workers=n)` 并发请求 Agent。

---

## 4. 后续更新流程

### 选项 A：完整重跑（推荐）

```bash
python -m training.gen_training_questions && \
python -m training.test_ask_graph && \
python -m training.model && \
python main.py
```

### 选项 B：只启动在线服务（模型已存在）

```bash
python main.py
```

---

## 5. 常见问题排查

### 5.1 找不到 `saves/model_best.pth`

原因：未完成步骤 1~3。

排查命令：

```bash
[ -f gened_questions/training_questions_for_graph.csv ] && echo "OK: question file" || echo "MISSING: run python -m training.gen_training_questions"
ls output_store/data_log/ask_graph_*.csv 2>/dev/null && echo "OK: data log" || echo "MISSING: run python -m training.test_ask_graph"
[ -f saves/model_best.pth ] && echo "OK: best model" || echo "MISSING: run python -m training.model"
```

### 5.2 `training/test_ask_graph.py` 连接失败或超时

原因：Agent 未启动、地址错误、网络不可达。

排查建议：
1. 检查 `config/config.yaml` 中 `server.host`、`server.port`。
2. 检查 Agent 健康状态与接口响应。
3. 必要时调整客户端重试或等待时间。

### 5.3 `training/model.py` 报数据集为空

原因：离线日志没有有效标签或日志文件为空。

排查命令：

```bash
head -20 output_store/data_log/ask_graph_*.csv
```

确保采样日志中有可用字段后，重新执行：

```bash
python -m training.test_ask_graph
python -m training.model
```

### 5.4 `main.py` 启动后页面不可访问

原因：端口占用或网络策略限制。

排查命令：

```bash
lsof -i :8090
```

根据结果释放端口或修改服务端口后重启。
