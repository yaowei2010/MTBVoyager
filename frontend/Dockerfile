# ---------- 1) Build stage（Node：build React） ----------
FROM node:20-alpine AS builder
WORKDIR /app

# 先只複製 package 檔，讓 cache 生效
COPY package*.json ./

# postinstall 會 cp 到 public，所以先建
RUN mkdir -p public

# 安裝依賴
RUN npm ci --legacy-peer-deps || npm i --legacy-peer-deps

# 再複製程式碼進來
COPY . .

# CRA 在 CI 環境下會把 warning 當 error，關掉比較穩
ENV CI=false

# build（會產生 /app/build）
RUN npm run build


# ---------- 2) Runtime stage（Nginx：serve 靜態檔） ----------
FROM nginx:1.27-alpine AS runner

# 先移除預設設定，換成我們自己的
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf

# 把 React build 出來的檔案丟給 Nginx
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

