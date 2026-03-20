# data-copilot-v2-controller 工作流说明（优化版）

## 1. 文档目标

本文档用于说明 controller 仓库的完整工作流，并与 README / 论文中的核心思想严格对齐：

1. 后端 Agent 负责“自然语言 -> 代码生成 -> 执行 -> 异常/断言回输重试”闭环。
2. 本仓库负责“并发预测 + 多路独立请求调度 + 训练数据闭环”。
3. 通过 BERT 回归模型预测单次成功概率，计算合理并发数，平衡成功率与调用成本。

## 2. 与 README / 论文对齐关系

README 与论文中提到两条学习线：

1. Retries 学习（预测最佳重试次数）。
2. Concurrent 学习（预测最佳并发数量）。

当前代码实现状态：

1. Concurrent 学习：已实现并在线生效。
2. Retries 学习：尚未单独建模，当前请求仍使用固定区间 `retries: [5, 5]`。

这与 README 中的“技术路线”一致，但需要明确当前阶段是“并发预测落地、重试预测待独立建模”。

## 3. 系统职责边界

1. 本仓库（controller）

- 启动本地交互界面（PyWebIO）。
- 预测成功率并映射并发数。
- 并发调用后端 Agent API。
- 采集离线日志并训练并发预测模型。

2. 后端仓库（data-copilot-v2）

- 解析自然语言问题。
- 调用 LLM 生成代码。
- 代码执行、异常回输、断言回输与重试。
- 返回图像/HTML 等可视化结果。

## 4. 在线推理工作流（main.py）

### 4.1 启动阶段

1. `config/get_config.py` 加载并校验 `config/config.yaml`。
2. `utils/paths.py` 创建运行目录（日志、输出、临时图像等）。
3. `utils/http_client.py` 初始化带重试/超时的 HTTP 客户端。
4. `training/predict.py` 按需（lazy）加载 tokenizer 和 `saves/model_best.pth`。

### 4.2 单次提问阶段

1. 用户输入问题。
2. `predict(question)` 预测单次请求成功概率 `p`。
3. 根据下式计算最小并发数 `n`，并裁剪到 `[1, 5]`：

$$
1 - (1-p)^n \ge 0.99
$$

4. 使用 `ThreadPoolExecutor(max_workers=n)` 并发调用 `POST /ask/graph-steps`。
5. 逐个解析响应：

- HTTP 和业务码均成功时，解码 `image_data(base64)` 并展示。
- 异常、超时、JSON 格式错误时，给出可追踪错误日志。

## 5. 离线训练闭环

### 5.1 训练问题生成

入口：`gen_training_questions.py`

1. 读取数据库结构、外键、注释。
2. 组装 prompt，调用 LLM 生成训练问题。
3. 保存到 `gened_questions/training_questions_for_graph.csv`。

### 5.2 批量采样与日志沉淀

入口：`test-ask-graph.py` / `test-ask-echart.py`

1. 读取训练问题并批量调用后端接口。
2. 保存成功产物（PNG/HTML）。
3. 将每次请求结果写入 `output_store/data_log/*.csv`。

### 5.3 标签加工

入口：`training/process_data.py`

1. 从日志中提取问题、状态码、重试使用次数、文件信息。
2. 聚合每个问题的成功率 `success_rate`。
3. 形成监督样本：

- 输入：question
- 标签：success_rate
- 辅助统计：retry_list

### 5.4 数据集构建

入口：`training/dataset.py`

1. `build_dataloaders()` 显式构建 train/val/test DataLoader。
2. 小样本场景自动降级，避免空切分报错。
3. 输出重叠统计用于泄漏检查。

### 5.5 模型训练

入口：`training/model.py`

1. 模型结构：`BERT pooled_output -> Linear(768->256) -> ReLU -> Linear(256->1)`。
2. 损失函数：`MSELoss`，优化器：`Adam`。
3. 以验证集平均绝对误差保存 `saves/model_best.pth`。
4. 周期保存 checkpoint，最终保存 `model_final_*.pth`。

## 6. 数据日志契约（ask_graph_1.csv）

按当前脚本约定，单行字段为：

1. 时间戳
2. question
3. 请求重试下界
4. 请求重试上界
5. 保留字段
6. 业务状态码
7. 实际重试使用下界
8. 实际重试使用上界
9. 输出文件路径
10. 保留字段

训练侧依赖字段 2、6、7、8、9。新增脚本已对短行和脏数据做防御式处理。

## 7. 稳健性增强点（本次优化）

1. 配置加载

- 启动时校验必填字段（`mysql` / `llm` / `server`）。
- 配置缺失或 YAML 非法时直接抛出清晰错误。

2. 数据库连接

- 启用 `pool_pre_ping`。
- 启动即执行连接验证，避免运行中才暴露连接问题。

3. HTTP 请求

- 统一 `utils/http_client.py`，提供超时、重试、指数退避、错误封装。
- 统一替换主入口与批处理脚本中的重复请求代码。

4. 预测与训练

- `training/predict.py` 改为 lazy-load，避免导入即失败。
- `training/dataset.py` 改为函数式构建，消除导入副作用。
- 训练与预测路径统一到 `utils/paths.py`。

5. 可读性

- 新增公共模块：`utils/paths.py`、`utils/logger.py`、`utils/http_client.py`、`utils/string_utils.py`。
- 统一路径、日志、错误处理模式，减少重复与行为漂移。

## 8. 运行顺序建议

1. 启动后端 Agent 服务（data-copilot-v2）。
2. 配置 `config/config.yaml` 和 API key 文件。
3. 在线体验：`python main.py`。
4. 训练数据生成：`python gen_training_questions.py`。
5. 采样日志：`python test-ask-graph.py`。
6. 训练模型：`python training/model.py`。

## 9. 目录职责（优化后）

1. `main.py`：在线问答入口与并发调度。
2. `training/`：标签加工、数据切分、模型训练、在线预测。
3. `config/`：配置读取与校验。
4. `data_access/`：数据库连接与结构读取。
5. `llm_access/`：LLM provider 和 API key 管理。
6. `utils/`：路径、日志、HTTP、CSV、字符串处理公共能力。

## 10. 后续建议

1. 将 Retries 学习从固定值升级为独立回归头（与 Concurrent 类似）。
2. 增加训练和采样脚本的单元测试与回归测试。
3. 将日志格式升级为 CSV + JSON 双轨，便于统计与故障追踪。
