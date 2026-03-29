# Database Query System Workflow

## 1. 文档目标

本文档仅保留 Controller 项目的运行总览与模块关系，不再展开并发训练步骤细节。

并发训练与预测模型的完整步骤文档已迁移至：`training/training_steps.md`

---

## 2. 总体架构

Controller 包含两条主线：

1. 训练/预测主线
   - 相关脚本已统一集成在 `training/` 目录。
   - 负责生成训练问题、离线采样、模型训练与在线推理。
2. 图形界面主线
   - 由 `main.py` 提供 `PyWebIO` 交互界面。
   - 根据预测成功率动态计算并发线程，调用 Agent 的 `/ask/graph-steps`。

---

## 3. 并发训练步骤入口

并发训练步骤说明请直接参考：`training/training_steps.md`

该文档包含：
1. 首次训练全流程。
2. 增量更新流程。
3. 常见问题排查与命令示例。

---

## 4. 在线运行入口

```bash
# 启动图形界面（会使用 training/predict.py 做在线预测）
python main.py
```

默认访问地址：`http://localhost:8090`

---

## 5. 文件职责速查表

| 文件 | 职责 | 是否需单独启动 |
|------|------|---|
| `main.py` | 图形界面与并发调度入口 | ✓ **是** |
| `training/gen_training_questions.py` | 生成训练问题 | ✓ **是** |
| `training/test_ask_graph.py` | 采样并沉淀离线日志 | ✓ **是** |
| `training/model.py` | 训练并保存预测模型 | ✓ **是** |
| `training/predict.py` | 在线推理 | ✗ 被 `main.py` 导入 |
| `training/process_data.py` | 训练数据聚合 | ✗ 被 `training/model.py` 调用 |
| `training/dataset.py` | 训练数据集构建 | ✗ 被 `training/model.py` 调用 |
| `config/get_config.py` | 配置加载 | ✗ 被各模块导入 |
| `data_access/db_conn.py` | 数据库连接 | ✗ 被各模块导入 |
| `utils/paths.py` | 路径与运行目录管理 | ✗ 被各模块导入 |
