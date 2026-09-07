# Non-root deployment image. See the release CI Docker report for execution evidence.
# Pin an approved image digest in your production pipeline.
FROM node:22.23.2-bookworm-slim
WORKDIR /app
COPY --chown=node:node package.json ./
COPY --chown=node:node public ./public
COPY --chown=node:node shared ./shared
COPY --chown=node:node src ./src
COPY --chown=node:node server ./server
COPY --chown=node:node tools ./tools
RUN mkdir -p /app/data && chown node:node /app/data && chmod 700 /app/data
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000 DB_PATH=/app/data/masar.sqlite ALLOW_REGISTRATION=false
# PUBLIC_ORIGIN must be set to the exact external HTTPS origin at deployment.
USER node
VOLUME ["/app/data"]
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD node -e "fetch('http://127.0.0.1:3000/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node","server/server.mjs"]
