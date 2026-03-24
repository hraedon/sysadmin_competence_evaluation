# Build context: sysadmin_competence_evaluation/
# docker build -f platform/Dockerfile -t assessment-app .

FROM node:20-alpine AS build
WORKDIR /build

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
