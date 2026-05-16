# 构建阶段
FROM node:18-alpine AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY . .
RUN npm run build

# 运行阶段 (利用 Nginx 动静分离，极省内存)
FROM nginx:stable-alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
# 如果有自定义 nginx 配置可以 copy 进去，否则默认 80 端口
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]