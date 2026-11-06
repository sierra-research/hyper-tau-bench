# web/leaderboard/Dockerfile — the τ^τ-bench site with a store of builds (server.mjs), for a
# stack that shows a run's build trajectories beside its own pages: Strata's compose files
# and chart build it at a pinned commit of this repository as the `hyper-tau` service, and
# its gateway proxies /hyper-tau/* to it. Build from the repository root:
#
#   docker build -f web/leaderboard/Dockerfile -t hyper-tau-site .
#   docker run --rm -p 8001:8001 -v hyper-tau-builds:/data hyper-tau-site
#
# SITE_BASE is the path the site is served under (its assets and routes are built for it).

FROM node:24-bookworm-slim AS build
WORKDIR /site
COPY web/leaderboard/package.json web/leaderboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/leaderboard/ ./
ARG SITE_BASE=/hyper-tau
ENV VITE_SITE_BASE=${SITE_BASE}
RUN npm run build

FROM node:24-bookworm-slim
WORKDIR /site
ARG SITE_BASE=/hyper-tau
ENV NODE_ENV=production PORT=8001 SITE_BASE=${SITE_BASE} DATA_DIR=/data
COPY --from=build /site/dist ./dist
COPY web/leaderboard/server.mjs ./server.mjs
# The builds a run lands live on /data; writable for any uid in group 0 (OpenShift runs
# the container as one), as for a named user.
RUN mkdir -p /data && chgrp -R 0 /data /site && chmod -R g=u /data /site
USER 1000:0
VOLUME /data
EXPOSE 8001
HEALTHCHECK --interval=5s --timeout=3s --retries=20 CMD node -e "fetch('http://127.0.0.1:'+process.env.PORT+'/health').then((r)=>process.exit(r.ok?0:1),()=>process.exit(1))"
CMD ["node", "server.mjs"]
