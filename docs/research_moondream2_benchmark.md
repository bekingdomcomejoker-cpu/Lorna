# Moondream2 benchmark implementation notes

## Local paired-model requirement

The official llama.cpp multimodal documentation states that a local vision-capable GGUF is loaded with `-m <model.gguf>` and its multimodal projector is supplied through `--mmproj <projector.gguf>`. Image input is passed through `--image <file>`. [1]

The user device inventory contains the matching pair:

- `moondream2-050824-q5k.gguf`
- `moondream2-mmproj-050824-f16.gguf`

Moondream’s project documentation includes the equivalent historical llama.cpp invocation using a text-model GGUF, `--mmproj`, `--image`, a prompt, temperature `0.1`, and context `2048`. [2]

## Lorna2 implication

The ordinary text benchmark runner must not select the projector as a model candidate. A dedicated Moondream2 benchmark path should require the paired projector and a stable local image fixture, pass `--mmproj` and `--image` only when advertised by the installed local binary, and report unsupported multimodal capability without changing model classification.

## References

[1]: https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md "llama.cpp multimodal documentation"
[2]: https://huggingface.co/vikhyatk/moondream2/discussions/12 "Moondream2 GGUF discussion"
