# syntax=docker/dockerfile:1
FROM node:22-alpine AS build-stage

# 将工作目录设置为 /app/Controller，确保后续的 npm 命令都在正确的目录下执行
WORKDIR /app/Controller

# 指定从构建上下文的 Controller 目录中拷贝 package.json
COPY Controller/package*.json ./

# 利用 BuildKit 挂载 npm 缓存
RUN --mount=type=cache,target=/app/Controller/.npm \
    npm set cache /app/Controller/.npm && \
    npm install --registry=https://registry.npmmirror.com

# 将整个 Controller 目录的代码拷贝进容器的工作目录
COPY Controller/ .

# 执行构建
RUN npm run build

# 第二阶段：生产环境
FROM nginx:stable-alpine AS production-stage

# 注意这里的路径，要从 /app/Controller/dist 提取构建好的静态文件
COPY --from=build-stage /app/Controller/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]