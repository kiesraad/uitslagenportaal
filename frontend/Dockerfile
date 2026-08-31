FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

EXPOSE 5173

CMD npm install && npm run dev -- --host 0.0.0.0
