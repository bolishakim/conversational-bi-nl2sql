# Frontend Dockerfile for Railway deployment
# Build context: thesis_nl2sql_app/frontend/ (Railway root directory)
FROM node:20-alpine

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./
RUN npm ci

# Copy all frontend source code
COPY . .

# NEXT_PUBLIC_* vars are baked into the build at compile time — must be a build arg
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3000

# Use Railway's dynamic PORT env var (Next.js natively respects PORT)
CMD sh -c "npm start -- -p ${PORT:-3000}"
