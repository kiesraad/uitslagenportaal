# Stage 1 - build the frontend
FROM node:24 AS builder

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# Build frontend
COPY . .
RUN npm run build

## Stage 2 - serve the built frontend using nginx
FROM nginx:stable-alpine AS server

# Copy the nginx config file
COPY .docker/prod.nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build from the first stage to the Nginx container
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 for Nginx
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
