#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PRIMARY_PYTHON="3.14.7"
FALLBACK_PYTHON="3.13.13"
WORKER_PORT=7860
STREAMLIT_PORT=8501
API_PORT=8000
WITH_API=0
SETUP_ONLY=0
WORKER_PID=""
API_PID=""

cd "$PROJECT_ROOT"

usage() {
    cat <<'EOF'
Usage: ./launch.sh [options]

Options:
  --with-api                Also start the localhost management API.
  --setup-only              Install and validate dependencies, then exit.
  --worker-port PORT        Pipecat worker port (default: 7860).
  --streamlit-port PORT     Streamlit port (default: 8501).
  --api-port PORT           Management API port (default: 8000).
  -h, --help                Show this help.
EOF
}

valid_port() {
    [[ "$1" =~ ^[0-9]+$ ]] && ((1 <= 10#$1 && 10#$1 <= 65535))
}

while (($#)); do
    case "$1" in
        --with-api) WITH_API=1; shift ;;
        --setup-only) SETUP_ONLY=1; shift ;;
        --worker-port|--streamlit-port|--api-port)
            option="$1"
            [[ $# -ge 2 ]] || { echo "Missing value for $option." >&2; exit 2; }
            valid_port "$2" || { echo "Invalid port for $option: $2" >&2; exit 2; }
            case "$option" in
                --worker-port) WORKER_PORT="$2" ;;
                --streamlit-port) STREAMLIT_PORT="$2" ;;
                --api-port) API_PORT="$2" ;;
            esac
            shift 2
            ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ "$(uname -m)" == "x86_64" ]] || {
    echo "Pipecat Voice Studio supports native x86-64 Linux only." >&2
    exit 1
}

glibc_version="$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{print $2}')"
[[ -n "$glibc_version" ]] || {
    echo "GNU glibc 2.34 or newer is required; musl Linux is not supported." >&2
    exit 1
}
awk -v current="$glibc_version" 'BEGIN {
    split(current, c, ".");
    exit !((c[1] > 2) || (c[1] == 2 && c[2] >= 34));
}' || {
    echo "glibc 2.34 or newer is required; found $glibc_version." >&2
    exit 1
}

if ! command -v uv >/dev/null 2>&1; then
    echo "uv was not found. Installing it with the official installer..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "Install curl or wget so the uv installer can be downloaded." >&2
        exit 1
    fi
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    hash -r
fi
command -v uv >/dev/null 2>&1 || {
    echo "uv was installed but is not available on PATH. Open a new shell and retry." >&2
    exit 1
}
echo "Using uv: $(command -v uv)"

if uv python find "$PRIMARY_PYTHON" >/dev/null 2>&1; then
    python_version="$PRIMARY_PYTHON"
elif uv python install "$PRIMARY_PYTHON"; then
    python_version="$PRIMARY_PYTHON"
else
    echo "Python $PRIMARY_PYTHON could not be installed; trying $FALLBACK_PYTHON." >&2
    uv python find "$FALLBACK_PYTHON" >/dev/null 2>&1 \
        || uv python install "$FALLBACK_PYTHON"
    python_version="$FALLBACK_PYTHON"
fi

if [[ ! -d .venv ]]; then
    uv venv --python "$python_version" .venv
fi
if ! uv sync --check --python "$python_version"; then
    uv sync --locked --python "$python_version"
fi

python_exe="$PROJECT_ROOT/.venv/bin/python"
[[ -x "$python_exe" ]] || {
    echo "The project virtual environment was not created at .venv." >&2
    exit 1
}
if ! "$python_exe" -c 'import dateutil, pandas' 2>/dev/null; then
    echo "Repairing the python-dateutil installation..."
    uv sync --locked --python "$python_version" --reinstall-package python-dateutil
    "$python_exe" -c 'import dateutil, pandas'
fi

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example."
fi
if ! grep -Eq '^[[:space:]]*OPENAI_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]#]+' .env \
    && [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "Warning: OPENAI_API_KEY is empty. Live voice and evaluations require a key." >&2
fi

frontend_dir="$PROJECT_ROOT/src/pipecat_voice_studio/ui/frontend"
shopt -s nullglob
javascript_assets=("$frontend_dir"/build/index-*.js)
css_assets=("$frontend_dir"/build/index-*.css)
shopt -u nullglob
if ((${#javascript_assets[@]} != 1 || ${#css_assets[@]} != 1)); then
    command -v npm >/dev/null 2>&1 || {
        echo "Frontend assets are missing. Install Node.js/npm, then retry." >&2
        exit 1
    }
    echo "Building missing frontend assets..."
    (
        cd "$frontend_dir"
        npm ci
        npm run build
    )
fi

if ((SETUP_ONLY)); then
    echo "Setup complete. Virtual environment: $python_exe"
    exit 0
fi

ports=("$WORKER_PORT" "$STREAMLIT_PORT")
((WITH_API)) && ports+=("$API_PORT")
if [[ "$(printf '%s\n' "${ports[@]}" | sort -u | wc -l)" -ne "${#ports[@]}" ]]; then
    echo "Worker, Streamlit, and API ports must be distinct." >&2
    exit 1
fi

port_available() {
    "$python_exe" - "$1" <<'PY'
import socket
import sys

with socket.socket() as sock:
    try:
        sock.bind(("127.0.0.1", int(sys.argv[1])))
    except OSError:
        raise SystemExit(1)
PY
}

for port in "${ports[@]}"; do
    port_available "$port" || {
        echo "Port $port is already in use. Stop the service or select another port." >&2
        exit 1
    }
done

export PVS_BOT_BASE_URL="http://127.0.0.1:$WORKER_PORT"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
log_directory="$PROJECT_ROOT/artifacts/launcher"
mkdir -p "$log_directory"
worker_out_log="$log_directory/worker.out.log"
worker_error_log="$log_directory/worker.err.log"
api_out_log="$log_directory/api.out.log"
api_error_log="$log_directory/api.err.log"

cleanup() {
    local pid
    for pid in "$API_PID" "$WORKER_PID"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

wait_for_endpoint() {
    local url="$1" pid="$2" name="$3" attempts=60
    for ((attempt = 1; attempt <= attempts; attempt++)); do
        kill -0 "$pid" 2>/dev/null || {
            echo "$name exited before it became ready." >&2
            return 1
        }
        if "$python_exe" - "$url" >/dev/null 2>&1 <<'PY'
import sys
import urllib.request

with urllib.request.urlopen(sys.argv[1], timeout=1) as response:
    if response.status >= 400:
        raise SystemExit(1)
PY
        then
            return 0
        fi
        sleep 0.5
    done
    echo "$name did not become ready within 30 seconds." >&2
    return 1
}

"$python_exe" -m pipecat_voice_studio.voice.bot \
    --host 127.0.0.1 \
    --port "$WORKER_PORT" \
    --allowed-origins \
    "http://localhost:$STREAMLIT_PORT" \
    "http://127.0.0.1:$STREAMLIT_PORT" \
    >"$worker_out_log" 2>"$worker_error_log" &
WORKER_PID=$!
echo "Starting Pipecat worker on http://127.0.0.1:$WORKER_PORT ..."
if ! wait_for_endpoint "http://127.0.0.1:$WORKER_PORT/status" "$WORKER_PID" "Pipecat worker"; then
    tail -n 40 "$worker_out_log" "$worker_error_log" 2>/dev/null || true
    exit 1
fi
echo "Pipecat worker is ready."

if ((WITH_API)); then
    "$python_exe" -m uvicorn pipecat_voice_studio.api.app:app \
        --host 127.0.0.1 --port "$API_PORT" \
        >"$api_out_log" 2>"$api_error_log" &
    API_PID=$!
    if ! wait_for_endpoint "http://127.0.0.1:$API_PORT/health" "$API_PID" "Management API"; then
        tail -n 40 "$api_out_log" "$api_error_log" 2>/dev/null || true
        exit 1
    fi
    echo "Management API: http://127.0.0.1:$API_PORT/docs"
fi

echo "Opening Streamlit at http://127.0.0.1:$STREAMLIT_PORT"
"$python_exe" -m streamlit run \
    src/pipecat_voice_studio/ui/streamlit_app.py \
    --server.address 127.0.0.1 \
    --server.port "$STREAMLIT_PORT"
