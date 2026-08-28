FROM node:24-slim

WORKDIR /app

COPY package.json package-lock.json ./
# postinstall runs during npm install; copy it before that step.
COPY scripts/install-playwright-chromium.mjs ./scripts/
# Playwright runs on the host / CI, not in this image.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN npm install

EXPOSE 5173

CMD npm install && npm run dev -- --host 0.0.0.0
