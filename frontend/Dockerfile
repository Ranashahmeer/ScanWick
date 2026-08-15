# Multi-stage build: compile the Vite SPA, then serve the static output
# with nginx. VITE_* vars are baked into the JS bundle at build time (Vite
# convention), so they must be passed as build args, not runtime env vars —
# set them as this Railway service's build-time variables.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL
ARG VITE_AUTH_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_AUTH_API_BASE_URL=$VITE_AUTH_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
# Railway assigns a different $PORT per deploy; nginx's own envsubst-based
# templating (built into the official image, /docker-entrypoint.d/20-envsubst-on-templates.sh)
# renders nginx.conf.template -> default.conf using it at container start.
ENV PORT=8080
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
