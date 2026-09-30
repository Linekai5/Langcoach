# Langcoach

Status: Active Development (Work in Progress)

Technical workspace and implementation files for local MLX model execution on Apple Silicon.

---

## Technical Stack & Architecture

### Stack
* Framework: Apple MLX (`mlx`, `mlx-lm`)
* Backend: Metal Performance Shaders (Apple Silicon Unified Memory)
* GUI Toolkit: CustomTkinter (`customtkinter`, `tkinter`)
* Python Target: 3.10+ (tested on 3.11, 3.14)

### Concurrency & Execution Model
* Main Thread: Tkinter event loop handling rendering, trackpad scrolling, and state updates.
* Inference Thread: Isolated background `MLXWorker` (`threading.Thread`) communicating via thread-safe task and result queues (`queue.Queue`).
* Memory Management: Explicit garbage collection (`gc.collect()`) and Metal cache purging (`mx.clear_cache()`) during model switching and unload cycles.
* Token Generation: Streaming generator (`stream_generate`) with live tokens/second profiling and prompt token pre-allocation.
* Reasoning Stream Parser: Token stream inspection for `<|channel>thought` and `<channel|>` delimiters to isolate reasoning chains from output text.

---

## Repository Components

* `gui_chat.py`: Desktop interface featuring live token streaming, context token gauge, reasoning mode toggle, and dynamic input height calculation.
* `chat.py`: Terminal-based interactive CLI runner utilizing `mlx_lm`.
* `start_chat.sh`: Shell entrypoint with automated virtual environment discovery (`.venv`, `~/.mlx-env`, `~/mlx-env`).
* `requirements.txt`: Python package specifications.
* `.gitignore`: Excludes weight binaries, checkpoints, virtual environments, and caches.

---

## Verified Model Checkpoints

Tested on Apple Silicon with mixed-precision quantization (`oQ`) and Multi-Token Prediction (MTP) heads:

| Checkpoint Name | Parameter Count | Quantization | Architecture Features |
| :--- | :--- | :--- | :--- |
| `gemma-4-E2B-it-oQ4-mtp` | 2B | 4-bit (`oQ4`) | MTP Speculative Head |
| `gemma-4-E2B-it-oQ6-mtp` | 2B | 6-bit (`oQ6`) | MTP Speculative Head |
| `gemma-4-E4B-it-oQ4-mtp` | 4B | 4-bit (`oQ4`) | MTP Speculative Head |

### Checkpoint Resolution Precedence
1. Environment variable: `$MLX_MODELS_DIR`
2. Local directory: `./models/`
3. User directory: `~/models/`

---

## Dependencies & Setup

### Requirements
```
mlx>=0.20.0
mlx-lm>=0.20.0
customtkinter>=6.0.0
darkdetect>=0.8.0
packaging>=24.0
transformers>=4.40.0
```

### Installation
```bash
git clone https://github.com/Linekai5/Langcoach.git
cd Langcoach

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Execution Commands

### Desktop GUI
```bash
./start_chat.sh
# or
python3 gui_chat.py
```

### Terminal CLI
```bash
python3 chat.py
```

### HTTP Server Mode (OpenAI Compatible)
```bash
python3 -m mlx_lm.server --model ~/models/gemma-4-E2B-it-oQ4-mtp --port 8080
```
