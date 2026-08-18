FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
# Playwright runs on the host / CI, not in this image.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
