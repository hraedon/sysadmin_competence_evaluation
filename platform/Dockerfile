# Build context: sysadmin_competence_evaluation/
# docker build -f platform/Dockerfile -t assessment-app .

FROM node:20-alpine AS build
WORKDIR /build

# VITE_CONTROLLER_KEY is injected at build time from a GHA/k8s secret.
# Vite bakes the value into the JS bundle. An empty string causes 403s
# rather than succeeding with a known default (see SEC-06).
ARG VITE_CONTROLLER_KEY=""
ENV VITE_CONTROLLER_KEY=$VITE_CONTROLLER_KEY

# Copy frontend source, scenarios, and core logic together
COPY platform/frontend/ ./frontend/
COPY scenarios/ ./scenarios/
COPY core/ ./core/

WORKDIR /build/frontend
RUN npm ci

# SCENARIOS_DIR is relative to /build/frontend (the CWD during prebuild)
ENV SCENARIOS_DIR=../scenarios
RUN npm run build

# Production image
FROM nginx:alpine
COPY --from=build /build/frontend/dist /usr/share/nginx/html
# Serve scenario files (artifact content) as static assets
COPY --from=build /build/scenarios /usr/share/nginx/html/scenarios
COPY platform/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
