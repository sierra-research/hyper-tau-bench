FROM node:24-bookworm-slim AS node-runtime

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG TAU2_SOURCE_REVISION=unknown
ARG CODEX_VERSION=0.144.6
ARG CLAUDE_CODE_VERSION=2.1.219
ARG OPENCODE_VERSION=1.18.23

LABEL org.opencontainers.image.revision="${TAU2_SOURCE_REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV TAU2_SOURCE_REVISION="${TAU2_SOURCE_REVISION}"
ENV CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
ENV DISABLE_UPDATES=1

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npm install --global \
        @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} \
        @openai/codex@${CODEX_VERSION} \
        opencode-ai@${OPENCODE_VERSION} \
    && npm cache clean --force

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        bubblewrap \
        build-essential \
        ca-certificates \
        curl \
        diffutils \
        ffmpeg \
        file \
        git \
        git-lfs \
        jq \
        less \
        libsndfile1 \
        lsof \
        openssh-client \
        patch \
        poppler-utils \
        portaudio19-dev \
        procps \
        qpdf \
        ripgrep \
        rsync \
        shellcheck \
        socat \
        sqlite3 \
        tree \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

# IBM Bob Shell is not on public npm. A tarball in docker/hyper-construction/vendor/
# (``npm pack`` of an installed Bob Shell: ``ibm-bob-<version>.tgz`` for the ``@ibm/bob``
# package of Shell 2.0.9 and later, ``bobshell-<version>.tgz`` before; gitignored) is
# installed when present, and the ``bob`` harness is refused at startup on an image
# built without one.
COPY docker/hyper-construction/vendor/ /opt/vendor/
RUN if ls /opt/vendor/*.tgz >/dev/null 2>&1; then \
        npm install --global /opt/vendor/*.tgz && npm cache clean --force && bob --version; \
    fi && rm -rf /opt/vendor

RUN git config --system init.defaultBranch main \
    && git config --system user.name "Developer" \
    && git config --system user.email "developer@workspace.local" \
    && git config --system --add safe.directory /workspace

# Prime Agent is left out of this fork's image: its install script now lands in
# ~/.local/share and no longer ships the prime-agent-runtime wheel the kernel venv
# step installed. Codex, Claude Code and OpenCode stay.

WORKDIR /opt/tau2

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data/tau2/user_simulator ./data/tau2/user_simulator
COPY docker/hyper-construction/strip_runtime_src.py /opt/build/strip_runtime_src.py

# Builder agents can read everything under /opt/tau2, so the runtime tree may
# ship only the modules the in-container runtime executes. The strip script
# holds the fail-closed allowlist: everything else under src/tau2/hyper —
# client-defect implementations, graders, client-simulator internals, task
# construction — is deleted, and the import checks below prove the stripped
# tree still serves sealed scoring, the MCP stub, and the gateway sidecar.
# The packages pinned below are installed in addition to the locked project
# set as runtime conveniences for Developer agents, not as tau2 dependencies:
# a parser for every document format kits ship (pdf/xlsx/docx/pptx), the
# plotting/ML stack common agent sandboxes carry, and pytest for self-tests.
# Package indexes have intermittently returned truncated large wheels under
# uv's default parallel downloader. Serialize downloads and cache completed
# archives across retries to keep the build resilient.
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_CONCURRENT_DOWNLOADS=1 uv sync --frozen --no-install-project \
    && UV_CONCURRENT_DOWNLOADS=1 uv pip install --python .venv/bin/python \
        "pypdf==6.9.2" "openpyxl==3.1.5" "python-docx==1.1.2" \
        "python-pptx==1.0.2" "pytest==9.0.1" "matplotlib==3.10.7" \
        "plotly==6.5.0" "seaborn==0.13.2" "scikit-learn==1.7.2" \
        "tokenizers==0.22.1" \
    && .venv/bin/python -c \
        "import docx, jinja2, jsonschema, litellm, matplotlib, numpy, openai, openpyxl, pandas, plotly, pptx, pydantic, pypdf, pytest, scipy, seaborn, sklearn, tiktoken, tokenizers" \
    && rm -rf data/tau2/domains \
    && .venv/bin/python /opt/build/strip_runtime_src.py \
    && rm -rf /opt/build \
    && PYTHONPATH=/opt/tau2/src .venv/bin/python -c \
        "import tau2.hyper.agent_context, tau2.hyper.client_api, \
tau2.hyper.runtime_contract, tau2.hyper.sandbox.candidate_server, \
tau2.hyper.sandbox.callback_mcp, tau2.hyper.sandbox.model_gateway, \
tau2.hyper.harnesses.codex_driver, \
tau2.hyper.harnesses.prompt_arg_driver, tau2.hyper.harnesses.turn_loop_driver, \
tau2.hyper.harnesses.otlp_sink_driver"

ENV PATH="/opt/tau2/.venv/bin:${PATH}"
ENV PYTHONPATH="/workspace:/opt/tau2/src"
ENV TAU2_DATA_DIR="/opt/tau2/data"

# Native coding harnesses commonly execute commands through `bash -lc`, and
# Debian's /etc/profile resets PATH for login shells. Restore the pinned Tau
# environment after that reset so direct commands and harness Bash agree.
RUN printf '%s\n' \
        'export PATH="/opt/tau2/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"' \
        'export PYTHONPATH="/workspace:/opt/tau2/src"' \
        'export TAU2_DATA_DIR="/opt/tau2/data"' \
        > /etc/profile.d/10-tau2-path.sh

WORKDIR /workspace

RUN codex --version \
    && claude --version \
    && opencode --version \
    && git --version \
    && rg --version \
    && tree --version \
    && pdftotext -v \
    && pdftoppm -v \
    && pdfinfo -v \
    && qpdf --version \
    && python -c "import pypdf; print('pypdf', pypdf.__version__)" \
    && python -c "import openpyxl; print('openpyxl', openpyxl.__version__)" \
    && python -c "import docx; print('python-docx', docx.__version__)" \
    && python -c "import pptx; print('python-pptx', pptx.__version__)"
