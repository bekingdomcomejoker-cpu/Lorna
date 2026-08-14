# SmolVLM-to-DeepSeek-Coder on Android Termux

Lorna2 can reconstruct code from a local screenshot or image using a **sequential** two-stage process. SmolVLM first converts the image into a compact, structured visual specification. The process exits before DeepSeek-Coder starts, ensuring that the vision model, its projector, and the code model do not occupy memory simultaneously.

> **The visual stage is an interpreter, not a code generator.** DeepSeek-Coder receives only the extracted layout specification and writes the implementation.

| Stage | Executable and model | Persistent output | Memory rule |
|---|---|---|---|
| Visual preprocessing | `llama-mtmd-cli`, SmolVLM-256M Q4, and its projector | `visual_spec.md` | Run first; use one image; SmolVLM exits completely. |
| Code generation | `llama-cli` and DeepSeek-Coder 1.3B Q4 | Requested source file | Starts only after a valid visual specification has been saved. |

## Prerequisites

The following local files are expected under `~/models/`:

```text
SmolVLM-256M-Instruct-Q4_K_M.gguf
mmproj-SmolVLM-256M-Instruct-f16.gguf
deepseek-coder-1.3b-instruct-q4_k_m.gguf
```

Use an up-to-date Termux llama.cpp build that provides both `llama-mtmd-cli` and `llama-cli`. The multimodal test executable is the recommended test and development path for local image/projector pairs. [1]

Stop the Ollama service before starting the pipeline. This preserves RAM and swap headroom for the currently active direct llama.cpp process:

```bash
pkill -f 'ollama serve' 2>/dev/null || true
```

## Lorna2 command

After pulling the integration, use Lorna2 as follows:

```bash
cd "$HOME/Lorna"
printf '/visual-code /sdcard/Download/screenshot.png /sdcard/Download/rebuilt_page.html\n/exit\n' | python3 agents/lorna_v2.py
```

The command stores its working artifacts under `~/.lorna_v2/visual_to_code/`:

```text
visual_spec.md
smolvlm_run.log
deepseek_coder_prompt.txt
deepseek_coder_run.log
```

These files make a failed stage inspectable and allow the code-generation prompt to be reused without reprocessing the image.

## Direct command and dry run

The underlying pipeline can also run directly. A dry run confirms all arguments without loading either model:

```bash
cd "$HOME/Lorna"
python3 agents/vision_to_code.py \
  /sdcard/Download/screenshot.png \
  --output /sdcard/Download/rebuilt_page.html \
  --dry-run
```

Run without `--dry-run` only after the single-image SmolVLM test is known to work:

```bash
python3 agents/vision_to_code.py \
  /sdcard/Download/screenshot.png \
  --output /sdcard/Download/rebuilt_page.html \
  --target 'responsive HTML and CSS'
```

The visual stage uses a 2,048-token context, small batch and micro-batch sizes, a 128-token image cap, CPU projector execution, and a single image. It streams `encoding mtmd batch` progress into both Termux and `smolvlm_run.log`; this encoding can take several minutes on the phone, so let advancing batch counts complete. A Ctrl+C now terminates only the active vision subprocess cleanly and prevents the code stage from starting.

The SmolVLM command uses a system prompt plus `agents/visual_spec.gbnf`, a local constrained grammar. It requires exactly this four-field envelope before DeepSeek-Coder may start:

```text
BEGIN_VISUAL_SPEC
layout: ...
elements: ...
style: ...
text: ...
END_VISUAL_SPEC
```

A natural-language response such as `Screen displaying a code reconstruction page.` is therefore retained in the diagnostic log but rejected as an insufficient handoff. The CLI’s non-Jinja template path is intentional: it preserves the media marker that `llama-mtmd-cli` automatically adds for a supplied image. A known SmolVLM Jinja-template media-marker issue was fixed upstream after earlier releases, so the non-Jinja path is the safer compatibility default for an unknown Android build. [2]

## Practical limits

This workflow is best for screenshots of landing pages, cards, dashboards, forms, and simple mobile layouts. A 256M vision model can miss tiny text, iconography, or exact dimensions. Treat its specification as a fast first draft. If a label, color, or spacing value matters, provide it in the code target or correct the saved `visual_spec.md` before rerunning only DeepSeek-Coder.

The pipeline intentionally refuses to start while `ollama serve` is detected. Pass `--allow-ollama` only when additional memory pressure is acceptable.

## References

[1]: https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md "llama.cpp multimodal documentation"

[2]: https://github.com/ggml-org/llama.cpp/issues/21634 "SmolVLM embedded Jinja template media-marker issue"
