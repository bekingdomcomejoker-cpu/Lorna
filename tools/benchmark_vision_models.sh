#!/data/data/com.termux/files/usr/bin/sh
# Sequential local vision benchmark for the verified Moondream2 and SmolVLM pairs.
# Each configuration runs one model at a time. Tuning lists create one-variable-
# at-a-time tests around the baseline; they never create a combinatorial grid.
#
# Examples:
#   benchmark-vision-models
#   benchmark-vision-models --threads 2,4 --output-tokens 16,24
#   benchmark-vision-models --threads 2,4 --batch-threads 2,4 \
#       --output-tokens 16,24 --image-tokens 32,64 image.jpg "Describe it."

set -u

HOME_DIR="${HOME:?HOME is required}"
LLAMA_MTMD="${LLAMA_MTMD_CLI:-llama-mtmd-cli}"
FIXTURE="$HOME_DIR/Lorna/agents/benchmark_assets/lorna_moondream_fixture.png"
IMAGE="$FIXTURE"
QUESTION="Describe the image in one short sentence."
DRY_RUN=0
SAVE_RESULTS="auto"
TIMEOUT_SECONDS="${VISION_BENCH_TIMEOUT_SECONDS:-180}"
LORNA_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
VISION_MEMORY_SCRIPT="$LORNA_DIR/agents/vision_benchmark_memory.py"
THREADS_LIST=""
BATCH_THREADS_LIST=""
OUTPUT_TOKENS_LIST=""
IMAGE_TOKENS_LIST=""

MOONDREAM_MODEL="$HOME_DIR/models/moondream2-text-model-q4_k_m-vicuna-20250414.gguf"
MOONDREAM_MMPROJ="$HOME_DIR/models/moondream2-mmproj-f16-20250414.gguf"
SMOLVLM_MODEL="$HOME_DIR/models/SmolVLM-256M-Instruct-Q4_K_M.gguf"
SMOLVLM_MMPROJ="$HOME_DIR/models/mmproj-SmolVLM-256M-Instruct-f16.gguf"

usage() {
    cat <<'EOF'
Usage:
  benchmark-vision-models [options] [image_path] [question]

Runs Moondream2 2025 and SmolVLM-256M sequentially against the same image.
A tuning list adds one-variable-at-a-time rows around each model's verified
baseline. Lists are comma-separated and are NOT combined into a grid.

Options:
  --dry-run                  Print planned commands; do not load models.
  --save-results             Persist parsed rows after completion (also permits dry-run records).
  --no-save-results          Do not update Lorna2 durable benchmark memory.
  --threads LIST             Generation + default batch threads, e.g. 2,4.
  --batch-threads LIST       Prompt/batch thread counts, e.g. 2,4.
  --output-tokens LIST       Generation caps (-n), e.g. 16,24,32.
  --image-tokens LIST        Vision limits, e.g. 32,64,auto.
                              'auto' uses the model's normal image setting.
  --timeout SECONDS          Per-run wall-clock safety bound (default: 180).
  --help                     Show this help.

Verified baselines:
  Moondream2: t=4, tb=4, n=24, ctx=1024, b/ub=32/32, image=64
  SmolVLM:    t=4, tb=4, n=32, ctx=2048, b/ub=8/8, image=auto

Examples:
  benchmark-vision-models --dry-run --threads 2,4 --output-tokens 16,24
  benchmark-vision-models --threads 2,4 --batch-threads 2,4 \
    --output-tokens 16,24 --image-tokens 32,64 \
    /sdcard/DCIM/Screenshots/example.jpg "Describe the screen."
EOF
}

need_option_value() {
    if [ "$#" -lt 2 ] || [ -z "$2" ]; then
        echo "Missing value for $1" >&2
        usage >&2
        exit 2
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --save-results)
            SAVE_RESULTS=1
            shift
            ;;
        --no-save-results)
            SAVE_RESULTS=0
            shift
            ;;
        --threads)
            need_option_value "$1" "${2:-}"
            THREADS_LIST="$2"
            shift 2
            ;;
        --batch-threads)
            need_option_value "$1" "${2:-}"
            BATCH_THREADS_LIST="$2"
            shift 2
            ;;
        --output-tokens)
            need_option_value "$1" "${2:-}"
            OUTPUT_TOKENS_LIST="$2"
            shift 2
            ;;
        --image-tokens)
            need_option_value "$1" "${2:-}"
            IMAGE_TOKENS_LIST="$2"
            shift 2
            ;;
        --timeout)
            need_option_value "$1" "${2:-}"
            TIMEOUT_SECONDS="$2"
            shift 2
            ;;
        --*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            if [ "$IMAGE" = "$FIXTURE" ]; then
                IMAGE="$1"
            elif [ "$QUESTION" = "Describe the image in one short sentence." ]; then
                QUESTION="$1"
            else
                echo "Too many positional arguments." >&2
                usage >&2
                exit 2
            fi
            shift
            ;;
    esac
done

is_positive_integer() {
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
        *) [ "$1" -gt 0 ] 2>/dev/null ;;
    esac
}

if ! is_positive_integer "$TIMEOUT_SECONDS"; then
    echo "--timeout must be a positive integer." >&2
    exit 2
fi

for required in "$MOONDREAM_MODEL" "$MOONDREAM_MMPROJ" "$SMOLVLM_MODEL" "$SMOLVLM_MMPROJ" "$IMAGE"; do
    if [ ! -r "$required" ]; then
        echo "Required file is not readable: $required" >&2
        exit 1
    fi
done

if ! command -v "$LLAMA_MTMD" >/dev/null 2>&1; then
    echo "llama-mtmd-cli is not installed or not on PATH." >&2
    exit 1
fi

if pgrep -f '[o]llama serve' >/dev/null 2>&1; then
    echo "Stop 'ollama serve' before benchmarking to keep one model in memory at a time." >&2
    exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${LORNA_VISION_BENCH_DIR:-$HOME_DIR/.lorna_v2/vision_bench}/$STAMP"
CONFIGS="$OUT_DIR/configurations.txt"
SUMMARY="$OUT_DIR/summary.txt"
mkdir -p "$OUT_DIR"
: > "$CONFIGS"

add_config() {
    label="$1"
    threads="$2"
    batch_threads="$3"
    output_tokens="$4"
    image_tokens="$5"
    key="$threads|$batch_threads|$output_tokens|$image_tokens"
    if ! grep -Fqx "$key" "$CONFIGS" 2>/dev/null; then
        printf '%s\n' "$key" >> "$CONFIGS"
        printf '%s|%s\n' "$label" "$key" >> "$OUT_DIR/labels.txt"
    fi
}

# The base configuration plus any requested one-variable-at-a-time candidates.
add_config "baseline" 4 4 default auto

if [ -n "$THREADS_LIST" ]; then
    for value in $(printf '%s' "$THREADS_LIST" | tr ',' ' '); do
        if ! is_positive_integer "$value"; then
            echo "Invalid thread count: $value" >&2
            exit 2
        fi
        add_config "threads=$value" "$value" "$value" default auto
    done
fi

if [ -n "$BATCH_THREADS_LIST" ]; then
    for value in $(printf '%s' "$BATCH_THREADS_LIST" | tr ',' ' '); do
        if ! is_positive_integer "$value"; then
            echo "Invalid batch-thread count: $value" >&2
            exit 2
        fi
        add_config "batch_threads=$value" 4 "$value" default auto
    done
fi

if [ -n "$OUTPUT_TOKENS_LIST" ]; then
    for value in $(printf '%s' "$OUTPUT_TOKENS_LIST" | tr ',' ' '); do
        if ! is_positive_integer "$value"; then
            echo "Invalid output-token limit: $value" >&2
            exit 2
        fi
        add_config "output_tokens=$value" 4 4 "$value" auto
    done
fi

if [ -n "$IMAGE_TOKENS_LIST" ]; then
    for value in $(printf '%s' "$IMAGE_TOKENS_LIST" | tr ',' ' '); do
        if [ "$value" != "auto" ] && ! is_positive_integer "$value"; then
            echo "Invalid image-token limit: $value" >&2
            exit 2
        fi
        add_config "image_tokens=$value" 4 4 default "$value"
    done
fi

label_for_key() {
    key="$1"
    sed -n "s/^[^|]*|$key\$/&/p" "$OUT_DIR/labels.txt" | head -n 1 | cut -d'|' -f1
}

run_moondream() {
    label="$1"; threads="$2"; batch_threads="$3"; token_override="$4"; image_override="$5"; run_id="$6"
    tokens="24"
    [ "$token_override" != "default" ] && tokens="$token_override"
    image_tokens="64"
    [ "$image_override" != "auto" ] && image_tokens="$image_override"
    log="$OUT_DIR/moondream2-${run_id}.log"
    start="$(date +%s)"

    if [ "$DRY_RUN" -eq 1 ]; then
        printf 'Moondream2 [%s]: %s -m %s --mmproj %s --image %s -p %s -t %s --threads-batch %s -n %s -c 1024 -b 32 --ubatch-size 32 --image-max-tokens %s\n' \
            "$label" "$LLAMA_MTMD" "$MOONDREAM_MODEL" "$MOONDREAM_MMPROJ" "$IMAGE" "$QUESTION" "$threads" "$batch_threads" "$tokens" "$image_tokens" > "$log"
        status=0
    else
        timeout -k 15s "${TIMEOUT_SECONDS}s" "$LLAMA_MTMD" \
            -m "$MOONDREAM_MODEL" --mmproj "$MOONDREAM_MMPROJ" --image "$IMAGE" -p "$QUESTION" \
            -n "$tokens" -c 1024 -t "$threads" --threads-batch "$batch_threads" -b 32 --ubatch-size 32 \
            --cache-type-k q4_0 --cache-type-v q4_0 --no-mmproj-offload \
            --image-max-tokens "$image_tokens" --temp 0.1 --perf > "$log" 2>&1
        status=$?
    fi
    elapsed=$(( $(date +%s) - start ))
    printf 'Moondream2 | %s | t=%s tb=%s n=%s image=%s | exit=%s | elapsed=%ss | log=%s\n' \
        "$label" "$threads" "$batch_threads" "$tokens" "$image_tokens" "$status" "$elapsed" "$log" | tee -a "$SUMMARY"
}

run_smolvlm() {
    label="$1"; threads="$2"; batch_threads="$3"; token_override="$4"; image_override="$5"; run_id="$6"
    tokens="32"
    [ "$token_override" != "default" ] && tokens="$token_override"
    log="$OUT_DIR/smolvlm-${run_id}.log"
    start="$(date +%s)"

    if [ "$DRY_RUN" -eq 1 ]; then
        printf 'SmolVLM [%s]: %s -m %s --mmproj %s --image %s -p %s --no-jinja --chat-template smolvlm -t %s --threads-batch %s -n %s -c 2048 -b 8 --ubatch-size 8' \
            "$label" "$LLAMA_MTMD" "$SMOLVLM_MODEL" "$SMOLVLM_MMPROJ" "$IMAGE" "$QUESTION" "$threads" "$batch_threads" "$tokens" > "$log"
        [ "$image_override" != "auto" ] && printf ' --image-max-tokens %s' "$image_override" >> "$log"
        printf '\n' >> "$log"
        status=0
    elif [ "$image_override" = "auto" ]; then
        timeout -k 15s "${TIMEOUT_SECONDS}s" "$LLAMA_MTMD" \
            -m "$SMOLVLM_MODEL" --mmproj "$SMOLVLM_MMPROJ" --image "$IMAGE" -p "$QUESTION" \
            --no-jinja --chat-template smolvlm \
            -n "$tokens" -c 2048 -t "$threads" --threads-batch "$batch_threads" -b 8 --ubatch-size 8 \
            --cache-type-k q4_0 --cache-type-v q4_0 --no-mmproj-offload --temp 0.1 --perf > "$log" 2>&1
        status=$?
    else
        timeout -k 15s "${TIMEOUT_SECONDS}s" "$LLAMA_MTMD" \
            -m "$SMOLVLM_MODEL" --mmproj "$SMOLVLM_MMPROJ" --image "$IMAGE" -p "$QUESTION" \
            --no-jinja --chat-template smolvlm \
            -n "$tokens" -c 2048 -t "$threads" --threads-batch "$batch_threads" -b 8 --ubatch-size 8 \
            --cache-type-k q4_0 --cache-type-v q4_0 --no-mmproj-offload \
            --image-max-tokens "$image_override" --temp 0.1 --perf > "$log" 2>&1
        status=$?
    fi
    elapsed=$(( $(date +%s) - start ))
    smol_image="$image_override"
    printf 'SmolVLM | %s | t=%s tb=%s n=%s image=%s | exit=%s | elapsed=%ss | log=%s\n' \
        "$label" "$threads" "$batch_threads" "$tokens" "$smol_image" "$status" "$elapsed" "$log" | tee -a "$SUMMARY"
}

{
    echo "Lorna sequential vision benchmark"
    echo "image=$IMAGE"
    echo "question=$QUESTION"
    echo "timeout=${TIMEOUT_SECONDS}s per model"
    echo "mode=one-variable-at-a-time"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "mode=dry-run"
    else
        echo "mode=benchmark"
    fi
    echo "output=$OUT_DIR"
    echo
} | tee "$SUMMARY"

run_id=0
while IFS='|' read -r threads batch_threads token_override image_override; do
    [ -z "$threads" ] && continue
    run_id=$((run_id + 1))
    key="$threads|$batch_threads|$token_override|$image_override"
    label="$(label_for_key "$key")"
    # An empty token override means each model retains its independently verified baseline.
    run_moondream "$label" "$threads" "$batch_threads" "$token_override" "$image_override" "$run_id"
    run_smolvlm "$label" "$threads" "$batch_threads" "$token_override" "$image_override" "$run_id"
done < "$CONFIGS"

printf '\nSummary saved to: %s\n' "$SUMMARY"
printf 'Configuration matrix: %s\n' "$CONFIGS"

# Actual benchmark rows update durable memory by default. A dry-run must opt in,
# so command previews never become recommended vision profiles.
should_save="$SAVE_RESULTS"
if [ "$DRY_RUN" -eq 1 ] && [ "$SAVE_RESULTS" = "auto" ]; then
    should_save=0
fi
if [ "$should_save" = "auto" ]; then
    should_save=1
fi
if [ "$should_save" -eq 1 ]; then
    if [ -r "$VISION_MEMORY_SCRIPT" ] && command -v python3 >/dev/null 2>&1; then
        printf 'Persisting vision benchmark rows in Lorna2 durable memory...\n'
        if python3 "$VISION_MEMORY_SCRIPT" ingest "$OUT_DIR"; then
            printf 'Vision benchmark memory updated. View in Lorna2 with /vision-results.\n'
        else
            printf 'Vision benchmark completed, but durable-memory ingestion failed. Ingest later with: /vision-ingest %s\n' "$OUT_DIR" >&2
        fi
    else
        printf 'Vision benchmark completed; durable-memory module unavailable. Ingest later with: /vision-ingest %s\n' "$OUT_DIR" >&2
    fi
else
    printf 'Durable-memory save skipped. Ingest later with: /vision-ingest %s\n' "$OUT_DIR"
fi
