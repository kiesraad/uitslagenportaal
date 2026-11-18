# Stage 1 - build the frontend
FROM node:24 AS builder

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build frontend
COPY . .
RUN npm run build

## Stage 2 - serve the built frontend with Node
FROM node:24-slim AS server

WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev

COPY --from=builder /app/build ./build
COPY server.js ./

USER node
EXPOSE 3000

CMD ["npm", "start"]
