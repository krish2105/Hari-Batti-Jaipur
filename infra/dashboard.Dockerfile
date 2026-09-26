# Signal Command dashboard image (P8 W18): Next.js production build served by `next start`.
# NEXT_PUBLIC_API_URL is baked in at build time (the CSP allows exactly that origin).
FROM node:24-slim AS build
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} NEXT_TELEMETRY_DISABLED=1
RUN corepack enable
WORKDIR /repo
COPY . .
RUN pnpm install --frozen-lockfile --filter dashboard... && pnpm --filter dashboard build

FROM node:24-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN corepack enable && useradd --uid 10001 --create-home app
WORKDIR /repo
COPY --from=build --chown=app /repo /repo
USER app
WORKDIR /repo/apps/dashboard
EXPOSE 3001
CMD ["pnpm", "exec", "next", "start", "--port", "3001"]
