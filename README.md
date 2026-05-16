# Database Query System - Controller (纯 Web 交互前端)

当前 Controller 项目已经被彻底剥离了所有的后台预测、训练和 Python 渲染逻辑任务。它目前转型为一个纯粹的、无后台逻辑运行的 **Vue 3 (Vite)** 前端单页面控制系统 (SPA)。

## 职能与交互逻辑

### 环境配置 (Conda)
为了方便新用户快速启动，建议使用 Conda 创建独立的 Python 运行环境，并依据项目中的 `requirement.txt` 安装相关依赖：
```bash
# 1. 创建名为 dqs 的 conda 环境 (Python 3.9)
conda create -n dqs python=3.9 -y

# 2. 激活环境
conda activate dqs

# 3. 安装项目依赖
pip install -r requirement.txt
```

- **职责**: 为终端用户展示统一的可视化交互入口界面（Login 交互、问题输入、加载拦截机制、结果图表瀑布流展示）。
- **微服务并行流**: 当用户触发数据绘制请求时，代码会通过 Web 浏览器中的 `fetch API` 进行网络拆分访问：
  1. 先向 `8001` (Database_Query_System_Training) 获取当前任务适合分发的并发请求数(预测成功概率计算)。
  2. 根据取到的数值，随后正式向 `8000` (Database_Query_System_Agent) 不断建立多重连接，从而绘制复杂的结构生成图谱。

## 运行方式
这是一个不含有任何挂起端口后台功能的完整前端项目，由于它的包名是 Node.Js 常规模块，只需利用 NPM 进行托管即可：
```bash
cd Controller
npm install
npm run dev
```
将热重载功能开启。该应用将会在默认的界面网址监听（通常为 http://localhost:5173/ \)。

## 使用 Docker 部署三个项目（分层优化磁盘占用）

在 `Database_Query_System_Controller` 根目录执行：

```bash
docker compose build
docker compose up -d
```

启动后端口映射：

- `5173 -> Controller (Nginx 静态站点)`
- `8000 -> Agent (Django)`
- `8001 -> Training (Django)`

访问地址：

- 前端：`http://localhost:5173`
- Agent API：`http://localhost:8000`
- Training API：`http://localhost:8001`

### 分层优化点

当前 Docker 方案使用了多层策略降低磁盘与构建开销：

1. **共享 Python 依赖基础层**：`Agent` 与 `Training` 都采用 `python-base` 构建阶段，先安装共同依赖，再在各自运行层叠加差异包。
2. **多阶段构建前端**：`Controller` 先用 `node:alpine` 构建静态资源，再复制到 `nginx:alpine` 运行层，避免把 Node 工具链带入最终镜像。
3. **精简构建上下文**：各仓库提供 `.dockerignore`，排除了 `node_modules`、缓存、日志、测试输出等无关文件。
4. **BuildKit 缓存挂载**：`pip` 与 `npm` 安装步骤使用缓存挂载，重复构建时可显著减少下载与构建时间。

### 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止并删除容器
docker compose down

# 停止并删除容器 + 网络 + 本地镜像
docker compose down --rmi local
```
