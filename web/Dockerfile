# -------- deps --------
FROM node:20-alpine AS deps
WORKDIR /app

# Needed by some npm packages on alpine
RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./

# Pick ONE based on your lockfile
RUN if [ -f package-lock.json ]; then npm ci; \
    elif [ -f pnpm-lock.yaml ]; then corepack enable && pnpm i --frozen-lockfile; \
    elif [ -f yarn.lock ]; then yarn --frozen-lockfile; \
    else echo "No lockfile found. Please commit a lockfile." && exit 1; fi


# -------- build --------
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build
RUN npm run build


# -------- runtime --------
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
# Azure typically injects PORT; default to 3000 locally
ENV PORT=80
ENV HOSTNAME=0.0.0.0

# Security: non-root user
RUN addgroup -S nextjs && adduser -S nextjs -G nextjs

# Standalone output files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/.next/standalone ./

USER nextjs

EXPOSE 80

# Standalone server.js is inside .next/standalone output we copied to /app
CMD ["node", "server.js"]
