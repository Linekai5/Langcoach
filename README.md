# Langcoach

> **Status:** 🚧 **Active Development (Work-in-Progress)**  
> *A native Apple Silicon desktop and terminal interface for running quantized Google Gemma models locally at high speeds using Apple MLX.*

---

## 📖 Overview

**Langcoach** is an open-source, local inference UI and CLI runner tailored for Apple Silicon (M1/M2/M3/M4). Powered by Apple's [MLX](https://github.com/ml-explore/mlx) framework, it takes full advantage of Unified Memory Architecture to run local Gemma LLMs with zero server overhead and low latency.

---

## ✨ What We Have Right Now

### 1. 🖥️ Desktop GUI (`gui_chat.py`)
A custom-tailored dark-mode desktop app built using `customtkinter`:
* **Real-Time Token Streaming:** Displays output tokens live with a dynamic speed counter (tokens/sec) and total generation time.
* **Context Usage Gauge:** Circular token percentage canvas indicating real-time context window consumption.
* **Extended Reasoning Mode:** Built-in toggle to parse and fold reasoning chains (handles `<|channel>thought` and `<channel|>` reasoning blocks seamlessly).
* **Smart Dynamic Input Dock:** Multi-line input area that automatically expands as you type (supports `Shift+Enter` for newlines and `Enter` to submit).
* **Model Management:** Dropdown selector to switch checkpoints with clean memory deallocation (`mx.clear_cache()` and garbage collection).
* **Trackpad & Wheel Precision:** 1-pixel trackpad inertia scrolling and copy-to-clipboard context menus.

### 2. 💻 Fast Terminal CLI (`chat.py`)
A lightweight, interactive command-line interface for testing and interacting with models directly in your terminal without any GUI dependencies.

### 3. 🚀 Automatic Launcher (`start_chat.sh`)
Shell script that automatically discovers virtual environments (`.venv`, `~/.mlx-env`, etc.) and boots up the GUI in one command.

---

## 🧠 Tested & Working Models

This project has been tested and verified with the following **Google Gemma 4** instruction-tuned models with mixed-precision quantization (`oQ`) and Multi-Token Prediction (MTP) heads:

| Model Checkpoint | Parameters | Quantization | Head | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`gemma-4-E2B-it-oQ4-mtp`** | 2 Billion | 4-bit (`oQ4`) | MTP Speculative Head | ✅ Verified / Fast |
| **`gemma-4-E2B-it-oQ6-mtp`** | 2 Billion | 6-bit (`oQ6`) | MTP Speculative Head | ✅ Verified / Balanced |
| **`gemma-4-E4B-it-oQ4-mtp`** | 4 Billion | 4-bit (`oQ4`) | MTP Speculative Head | ✅ Verified / High Quality |

### Model Directory Resolution
The application automatically checks for model checkpoints in:
1. Custom directory set via `MLX_MODELS_DIR` environment variable
2. Local project directory: `./models/`
3. User home directory: `~/models/`

*(Note: Model weight files such as `.safetensors` and `.bin` are excluded from Git via `.gitignore` due to file size limits).*

---

## ⚙️ Requirements & Prerequisites

* **Hardware:** Apple Silicon Mac (M1 / M2 / M3 / M4, Pro, Max, or Ultra)
* **OS:** macOS Ventura (13.0) or later
* **Python:** 3.10+ (tested on Python 3.14 & 3.11)

---

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AIkai1/Langcoach.git
   cd Langcoach
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add Models:**
   Place your MLX-quantized model folders into `~/models` or `./models/`.

---

## 🚀 How to Run

### Option A: Launch GUI Studio (Recommended)
Run using the launch script:
```bash
./start_chat.sh
```
Or run directly with Python:
```bash
python3 gui_chat.py
```

### Option B: Launch Terminal Chat
```bash
python3 chat.py
```

### Option C: Serve via MLX OpenAI-Compatible Server
```bash
python3 -m mlx_lm.server --model ~/models/gemma-4-E2B-it-oQ4-mtp --port 8080
```

---

## 🗺️ Roadmap & Next Steps

* [ ] Session history persistence (SQLite or JSON storage)
* [ ] Custom system prompt editor in GUI settings
* [ ] Multi-token speculative decoding parameter controls
* [ ] Vision / multimodal image input support
* [ ] Conversation export (Markdown / JSON)

---

## 📄 License

This project is licensed under the MIT License.
