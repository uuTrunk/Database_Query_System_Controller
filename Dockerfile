# syntax=docker/dockerfile:1
# 第一阶段：构建阶段 (使用 Node.js 22 兼容 Vite)
FROM node:22-alpine AS build-stage

# 将工作目录设置为 /app/Controller
WORKDIR /app/Controller

# 从根上下文将 package.json 拷贝进来
COPY Controller/package*.json ./

# 利用 BuildKit 挂载 npm 缓存，加速后续构建
RUN --mount=type=cache,target=/app/Controller/.npm \
    npm set cache /app/Controller/.npm && \
    npm install --registry=https://registry.npmmirror.com

# 拷贝所有前端源码
COPY Controller/ .

# 执行生产环境打包
RUN npm run build

# 第二阶段：生产环境展示
FROM nginx:stable-alpine AS production-stage

# 从第一阶段提取 dist 文件夹到 Nginx 默认目录
COPY --from=build-stage /app/Controller/dist /usr/share/nginx/html

EXPOSE 80

# 保持 Nginx 前台运行
CMD ["nginx", "-g", "daemon off;"]