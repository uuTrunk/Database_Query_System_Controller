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
