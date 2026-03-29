# Build context: sysadmin_competence_evaluation/
# docker build -f platform/Dockerfile -t assessment-app .

FROM node:20-alpine AS build
WORKDIR /build

# Copy root manifest and lockfile
COPY package.json package-lock.json ./

# Copy workspace members
COPY core/ ./core/
COPY platform/frontend/ ./platform/frontend/
COPY scenarios/ ./scenarios/

# Install dependencies for all workspaces
RUN npm ci

# Build the frontend
WORKDIR /build/platform/frontend
# SCENARIOS_DIR is relative to the directory where 'npm run build' (prebuild) runs
ENV SCENARIOS_DIR=../../scenarios
RUN npm run build

# Production image
FROM nginx:alpine
COPY --from=build /build/platform/frontend/dist /usr/share/nginx/html
# Serve scenario files (artifact content) as static assets
COPY --from=build /build/scenarios /usr/share/nginx/html/scenarios
COPY platform/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
