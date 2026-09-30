import os
import sys
import glob
import time
import gc
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
import mlx.core as mx
from mlx_lm import load, stream_generate

# Base appearance configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Design Tokens — True Dark, Flat Matte, Solid Fills
COLOR_CANVAS = "#000000"
COLOR_SURFACE_CARD = "#0C0C0C"
COLOR_SURFACE_PANEL = "#0F0F0F"
COLOR_BORDER_SUBTLE = "#1C1C1C"
COLOR_BORDER_FOCUS = "#2E2E2E"

# Chat Layout Styling
COLOR_USER_BUBBLE = "#161616"
COLOR_USER_BORDER = "#222222"
COLOR_SYSTEM_PILL = "#0A0A0A"
COLOR_SYSTEM_BORDER = "#161616"

# Interactive Elements
COLOR_INPUT_BG = "#0B0B0B"
COLOR_INPUT_BORDER = "#1E1E1E"

COLOR_BTN_PRIMARY_BG = "#181818"
COLOR_BTN_PRIMARY_HOVER = "#222222"
COLOR_BTN_PRIMARY_BORDER = "#252525"

COLOR_BTN_SECONDARY_BG = "#101010"
COLOR_BTN_SECONDARY_HOVER = "#181818"
COLOR_BTN_SECONDARY_BORDER = "#1C1C1C"

COLOR_BTN_DANGER_BG = "#1E1212"
COLOR_BTN_DANGER_HOVER = "#2A1818"
COLOR_BTN_DANGER_BORDER = "#381E1E"
COLOR_BTN_DANGER_TEXT = "#B86666"

COLOR_REASONING_ON_BG = "#15181C"
COLOR_REASONING_ON_HOVER = "#1D2128"
COLOR_REASONING_ON_BORDER = "#262C36"
COLOR_REASONING_ON_TEXT = "#BAC3CE"

COLOR_REASONING_OFF_BG = "#101010"
COLOR_REASONING_OFF_HOVER = "#181818"
COLOR_REASONING_OFF_BORDER = "#1C1C1C"
COLOR_REASONING_OFF_TEXT = "#666D7A"

# Typographic Scale
COLOR_TEXT_PRIMARY = "#E0E0E0"
COLOR_TEXT_SECONDARY = "#949BA6"
COLOR_TEXT_MUTED = "#646B78"
COLOR_TEXT_DIM = "#404652"
COLOR_STATS_TEXT = "#4E5462"
COLOR_TEXT_ERROR = "#9E5959"
COLOR_STATUS_IDLE = "#646B78"
COLOR_STATUS_ACTIVE = "#8E95A3"

FONT_FAMILY = "-apple-system"
CONTEXT_OPTIONS = ["2048", "4096", "8192", "16384"]

# Dynamic Input Box Sizing Constants
INPUT_MIN_HEIGHT = 38
INPUT_MAX_HEIGHT = 140
INPUT_LINE_HEIGHT = 18

def get_models_dir():
    env_dir = os.environ.get("MLX_MODELS_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    if os.path.isdir(local_dir):
        return local_dir
    return os.path.expanduser("~/models")

def get_models():
    models_dir = get_models_dir()
    return sorted([os.path.basename(f) for f in glob.glob(os.path.join(models_dir, "*")) if os.path.isdir(f)])

class SelectableMessageText(tk.Text):
    """
    Minimalist, read-only, selectable & copyable typography widget.
    Allows mouse/trackpad drag highlighting, word/line selection, Cmd+C / Ctrl+C copying,
    and dark-mode context menus, while strictly blocking arbitrary editing.
    Seamlessly forwards trackpad gestures (<TouchpadScroll>) and mouse wheel (<MouseWheel>)
    to the chat canvas with 1-pixel precision.
    """
    def __init__(self, master, font=None, bg=COLOR_CANVAS, fg=COLOR_TEXT_PRIMARY, app=None, width=None, **kwargs):
        kw = {
            "font": font or (FONT_FAMILY, 14),
            "bg": bg,
            "fg": fg,
            "wrap": "word",
            "borderwidth": 0,
            "highlightthickness": 0,
            "padx": 0,
            "pady": 0,
            "insertwidth": 0,
            "exportselection": False,
            "selectbackground": "#2F3542",
            "selectforeground": "#FFFFFF",
            "inactiveselectbackground": "#22262E",
            "cursor": "xterm",
            "height": 1,
            "relief": "flat"
        }
        if width is not None:
            kw["width"] = width
        kw.update(kwargs)
        super().__init__(master, **kw)
        self.app = app
        self.configure(state="disabled")
        self._init_bindings()

    def _init_bindings(self):
        # Forward trackpad and mouse wheel to App's global handlers & prevent Text internal scroll
        if self.app:
            self.bind("<TouchpadScroll>", self._on_touchpad, add="+")
            self.bind("<MouseWheel>", self._on_wheel, add="+")
        
        # Copy and select-all keyboard shortcuts
        self.bind("<Mod1-Key-c>", self.copy_to_clipboard)
        self.bind("<Control-Key-c>", self.copy_to_clipboard)
        self.bind("<<Copy>>", self.copy_to_clipboard)
        self.bind("<Mod1-Key-a>", self.select_all)
        self.bind("<Control-Key-a>", self.select_all)
        self.bind("<<SelectAll>>", self.select_all)
        
        # Context menu bindings
        self.bind("<Button-2>", self.show_context_menu)
        self.bind("<Button-3>", self.show_context_menu)
        self.bind("<Control-Button-1>", self.show_context_menu)

    def _on_touchpad(self, event):
        if self.app and hasattr(self.app, "on_touchpad_scroll"):
            self.app.on_touchpad_scroll(event)
        return "break"

    def _on_wheel(self, event):
        if self.app and hasattr(self.app, "on_mouse_wheel"):
            self.app.on_mouse_wheel(event)
        return "break"

    def get_text(self):
        return self.get("1.0", "end-1c")

    def cget(self, key):
        if key == "text":
            return self.get_text()
        return super().cget(key)

    def set_text(self, text):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.insert("1.0", text)
        self.configure(state="disabled")
        self.update_height()

    def append_text(self, chunk):
        self.configure(state="normal")
        self.insert("end", chunk)
        self.configure(state="disabled")
        self.update_height()

    def update_height(self):
        try:
            self.update_idletasks()
            dl = self.count("1.0", "end", "displaylines")
            if dl and dl[0] is not None:
                lines = max(1, dl[0])
                if self.cget("height") != lines:
                    self.configure(height=lines)
        except Exception:
            pass

    def recalculate_user_width(self, max_w_px, text):
        try:
            f = tkfont.Font(font=self.cget("font"))
            char_w = max(1, f.measure("0"))
            lines = text.split("\n")
            longest_line_px = max((f.measure(l) for l in lines), default=0)
            target_px = max(50, min(longest_line_px + 8, max_w_px))
            chars = max(4, int(target_px / char_w) + 1)
            self.configure(width=chars)
            self.update_height()
        except Exception:
            pass

    def copy_to_clipboard(self, event=None):
        try:
            text = self.get("sel.first", "sel.last")
        except Exception:
            text = self.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
        return "break"

    def select_all(self, event=None):
        self.tag_add("sel", "1.0", "end-1c")
        return "break"

    def show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        has_sel = False
        try:
            sel_text = self.get("sel.first", "sel.last")
            if sel_text:
                has_sel = True
        except Exception:
            pass
            
        if has_sel:
            menu.add_command(label="Copy Selection", command=self.copy_to_clipboard)
        menu.add_command(label="Copy Entire Message", command=self._copy_all)
        menu.add_separator()
        menu.add_command(label="Select All", command=self.select_all)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _copy_all(self):
        text = self.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

class MLXWorker(threading.Thread):
    def __init__(self, task_queue, result_queue):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.model = None
        self.tokenizer = None
        self.loaded_model_name = None
        self.stop_event = threading.Event()

    def run(self):
        while True:
            action, payload = self.task_queue.get()
            if action == "load":
                model_name, model_path = payload
                self._unload_current()
                try:
                    t0 = time.time()
                    self.model, self.tokenizer = load(model_path)
                    duration = time.time() - t0
                    self.loaded_model_name = model_name
                    self.result_queue.put(("load_success", (model_name, duration)))
                except Exception as e:
                    self.result_queue.put(("load_error", str(e)))
                    
            elif action == "generate":
                messages, max_tokens, enable_thinking = payload
                if self.model is None or self.tokenizer is None:
                    self.result_queue.put(("gen_error", "No model loaded."))
                    continue
                    
                self.stop_event.clear()
                try:
                    prompt = self.tokenizer.apply_chat_template(
                        messages, 
                        tokenize=False, 
                        add_generation_prompt=True,
                        enable_thinking=enable_thinking
                    )
                    
                    try:
                        prompt_tokens = len(self.tokenizer.encode(prompt))
                    except Exception:
                        prompt_tokens = sum(len(m.get("content", "").split()) * 4 // 3 for m in messages)
                    self.result_queue.put(("context_update", prompt_tokens))
                    
                    token_count = 0
                    t_start = time.perf_counter()
                    first_token_time = None
                    raw_accum = ""
                    in_thought = False
                    thought_finished = False
                    final_answer = ""
                    
                    for resp in stream_generate(self.model, self.tokenizer, prompt=prompt, max_tokens=max_tokens):
                        if self.stop_event.is_set():
                            break
                            
                        now = time.perf_counter()
                        if first_token_time is None:
                            first_token_time = now
                            
                        chunk = resp.text
                        token_count += 1
                        raw_accum += chunk
                        
                        duration = now - first_token_time
                        tps = (token_count - 1) / duration if (duration > 0 and token_count > 1) else 0.0
                        total_ctx = prompt_tokens + token_count
                        
                        if enable_thinking and not thought_finished:
                            if "<|channel>thought" in raw_accum and not in_thought:
                                in_thought = True
                                self.result_queue.put(("thought_start", None))
                                
                            if "<channel|>" in raw_accum:
                                in_thought = False
                                thought_finished = True
                                self.result_queue.put(("thought_end", None))
                                answer_start = raw_accum.split("<channel|>")[-1]
                                if answer_start:
                                    final_answer += answer_start
                                    self.result_queue.put(("answer_chunk", (answer_start, tps, token_count, total_ctx)))
                            else:
                                if in_thought:
                                    self.result_queue.put(("thought_chunk", (tps, token_count, total_ctx)))
                                else:
                                    if not raw_accum.startswith("<|channel>"):
                                        thought_finished = True
                                        final_answer += raw_accum
                                        self.result_queue.put(("answer_chunk", (raw_accum, tps, token_count, total_ctx)))
                        else:
                            final_answer += chunk
                            self.result_queue.put(("answer_chunk", (chunk, tps, token_count, total_ctx)))
                            
                    total_time = time.perf_counter() - (first_token_time or t_start)
                    final_tps = token_count / total_time if total_time > 0 else 0.0
                    self.result_queue.put(("gen_done", (final_answer.strip(), token_count, total_time, final_tps, self.stop_event.is_set(), prompt_tokens + token_count)))
                except Exception as e:
                    self.result_queue.put(("gen_error", str(e)))
                    
            elif action == "unload":
                self._unload_current()
                self.result_queue.put(("unload_done", None))
                
            elif action == "stop":
                self._unload_current()
                break

    def _unload_current(self):
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            self.loaded_model_name = None
            gc.collect()
            mx.clear_cache()

class _DummyWidget:
    def configure(self, *args, **kwargs):
        pass
    def pack(self, *args, **kwargs):
        pass
    def pack_forget(self, *args, **kwargs):
        pass
    def grid(self, *args, **kwargs):
        pass
    def grid_forget(self, *args, **kwargs):
        pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MLX Studio")
        self.geometry("1020x760")
        self.minsize(760, 540)
        self.configure(fg_color=COLOR_CANVAS)
        
        # Native macOS window alpha
        try:
            self.wm_attributes("-alpha", 0.97)
        except Exception:
            pass
            
        self.messages = []
        self.context_size = 4096
        self.is_generating = False
        self.reasoning_enabled = False
        self.is_loading = False
        self.thinking_active = False
        self.is_confirming_disconnect = False
        self.disconnect_reset_timer = None
        
        self.anim_step = 0
        self.current_context_tokens = 0
        self.is_thinking = False
        self.current_thinking_label = None
        self.current_asst_footer = None
        self.current_asst_label = None
        self.current_asst_text = None
        self.current_asst_stats = None
        self.current_asst_copy_btn = None
        self.current_thought_label = None
        self.bubble_items = []
        self.speed_label = _DummyWidget()
        
        # Smart Auto-Scroll Pinning State
        self.auto_scroll_pinned = True
        
        # Communication queues
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        self.worker = MLXWorker(self.task_queue, self.result_queue)
        self.worker.start()
        
        self.setup_ui()
        self.after(20, self.poll_worker)
        
    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # ----------------- View 1: Setup / Model Selection Screen -----------------
        self.setup_container = ctk.CTkFrame(self, fg_color=COLOR_CANVAS)
        self.setup_container.grid(row=0, column=0, sticky="nsew")
        self.setup_container.grid_rowconfigure(0, weight=1)
        self.setup_container.grid_columnconfigure(0, weight=1)
        
        self.setup_card = ctk.CTkFrame(
            self.setup_container, 
            corner_radius=20,
            fg_color=COLOR_SURFACE_CARD,
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE
        )
        self.setup_card.grid(row=0, column=0, padx=60, pady=50)
        self.setup_card.grid_columnconfigure(0, weight=1)
        
        # Typography Header
        title_label = ctk.CTkLabel(
            self.setup_card, 
            text="MLX INFERENCE", 
            font=(FONT_FAMILY, 20, "bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, pady=(48, 6), padx=60)
        
        subtitle = ctk.CTkLabel(
            self.setup_card, 
            text="Apple Silicon Unified Architecture  •  Zero Server Overhead", 
            font=(FONT_FAMILY, 12), 
            text_color=COLOR_TEXT_MUTED
        )
        subtitle.grid(row=1, column=0, pady=(0, 36), padx=60)
        
        # Model Dropdown Field
        ctk.CTkLabel(
            self.setup_card, 
            text="MODEL CHECKPOINT", 
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLOR_TEXT_MUTED
        ).grid(row=2, column=0, pady=(0, 6))
        
        models = get_models()
        self.model_var = ctk.StringVar(value=models[0] if models else "No models found")
        self.model_dropdown = ctk.CTkOptionMenu(
            self.setup_card, 
            variable=self.model_var, 
            values=models, 
            width=380, 
            height=40,
            font=(FONT_FAMILY, 13),
            fg_color=COLOR_INPUT_BG,
            button_color=COLOR_BTN_PRIMARY_BG,
            button_hover_color=COLOR_BTN_PRIMARY_HOVER,
            dropdown_fg_color=COLOR_SURFACE_CARD,
            dropdown_hover_color=COLOR_BTN_PRIMARY_HOVER,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=10
        )
        self.model_dropdown.grid(row=3, column=0, pady=(0, 22), padx=60)
        
        # Context Window Dropdown (4 curated options)
        ctk.CTkLabel(
            self.setup_card, 
            text="CONTEXT WINDOW (TOKENS)", 
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLOR_TEXT_MUTED
        ).grid(row=4, column=0, pady=(0, 6))
        
        self.context_var = ctk.StringVar(value="4096")
        self.context_dropdown = ctk.CTkOptionMenu(
            self.setup_card,
            variable=self.context_var,
            values=CONTEXT_OPTIONS,
            width=200,
            height=40,
            font=(FONT_FAMILY, 13),
            fg_color=COLOR_INPUT_BG,
            button_color=COLOR_BTN_PRIMARY_BG,
            button_hover_color=COLOR_BTN_PRIMARY_HOVER,
            dropdown_fg_color=COLOR_SURFACE_CARD,
            dropdown_hover_color=COLOR_BTN_PRIMARY_HOVER,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=10
        )
        self.context_dropdown.grid(row=5, column=0, pady=(0, 24))
        
        # Reasoning Switch
        self.setup_reasoning_switch = ctk.CTkSwitch(
            self.setup_card,
            text="Reasoning Mode (Extended Thinking Chain)",
            font=(FONT_FAMILY, 12),
            text_color=COLOR_TEXT_SECONDARY,
            progress_color=COLOR_BTN_PRIMARY_HOVER,
            button_color=COLOR_TEXT_PRIMARY,
            button_hover_color=COLOR_TEXT_PRIMARY,
            command=self.on_setup_reasoning_toggle
        )
        self.setup_reasoning_switch.grid(row=6, column=0, pady=(0, 30))
        if self.reasoning_enabled:
            self.setup_reasoning_switch.select()
        else:
            self.setup_reasoning_switch.deselect()
        
        # Initialize Button
        self.load_btn = ctk.CTkButton(
            self.setup_card, 
            text="INITIALIZE SESSION", 
            font=(FONT_FAMILY, 12, "bold"), 
            width=230, 
            height=44, 
            fg_color=COLOR_BTN_PRIMARY_BG,
            hover_color=COLOR_BTN_PRIMARY_HOVER,
            border_width=1,
            border_color=COLOR_BTN_PRIMARY_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=10,
            command=self.on_load_click
        )
        self.load_btn.grid(row=7, column=0, pady=(0, 16))
        
        # Status Label
        self.status_label = ctk.CTkLabel(
            self.setup_card, 
            text="", 
            font=(FONT_FAMILY, 11), 
            text_color=COLOR_TEXT_MUTED
        )
        self.status_label.grid(row=8, column=0, pady=(0, 40))
        
        # ----------------- View 2: Minimalist Chat Interface -----------------
        self.chat_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_CANVAS)
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Sleek Minimalist Header Bar
        self.top_bar = ctk.CTkFrame(
            self.chat_frame, 
            height=50, 
            corner_radius=12, 
            fg_color=COLOR_SURFACE_PANEL,
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE
        )
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(14, 8))
        self.top_bar.grid_columnconfigure(1, weight=1)
        
        self.model_info_label = ctk.CTkLabel(
            self.top_bar, 
            text="", 
            font=(FONT_FAMILY, 12, "bold"), 
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w"
        )
        self.model_info_label.grid(row=0, column=0, padx=18, pady=10)
        
        # Context Window Percentage Gauge (Little circle that fills up, percentage in middle, no text)
        self.context_gauge = tk.Canvas(
            self.top_bar,
            width=36,
            height=36,
            bg=COLOR_SURFACE_CARD,
            highlightthickness=0,
            bd=0
        )
        self.context_gauge.grid(row=0, column=1, padx=10, pady=4)
        try:
            self.context_gauge.bind("<TouchpadScroll>", self.on_touchpad_scroll)
            self.context_gauge.bind("<MouseWheel>", self.on_mouse_wheel)
        except Exception:
            pass
        
        # Action Buttons Container (Disconnect Confirmation Zone)
        self.right_controls = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.right_controls.grid(row=0, column=2, padx=14, pady=6, sticky="e")
        
        self.reasoning_btn = ctk.CTkButton(
            self.right_controls,
            text="REASONING: OFF",
            width=124,
            height=30,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLOR_REASONING_OFF_BG,
            hover_color=COLOR_REASONING_OFF_HOVER,
            border_width=1,
            border_color=COLOR_REASONING_OFF_BORDER,
            text_color=COLOR_REASONING_OFF_TEXT,
            corner_radius=8,
            command=self.toggle_reasoning
        )
        self.reasoning_btn.pack(side="left", padx=(0, 8))
        
        # Disconnect Confirmation Cluster
        self.disconnect_cluster = ctk.CTkFrame(self.right_controls, fg_color="transparent")
        self.disconnect_cluster.pack(side="left")
        
        self.disconnect_btn = ctk.CTkButton(
            self.disconnect_cluster, 
            text="DISCONNECT", 
            width=100, 
            height=30, 
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLOR_BTN_SECONDARY_BG,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=COLOR_BTN_SECONDARY_BORDER,
            text_color=COLOR_TEXT_SECONDARY,
            corner_radius=8,
            command=self.show_disconnect_confirm
        )
        self.disconnect_btn.pack(side="left")
        
        self.confirm_disconnect_btn = ctk.CTkButton(
            self.disconnect_cluster, 
            text="CONFIRM?", 
            width=84, 
            height=30, 
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLOR_BTN_DANGER_BG,
            hover_color=COLOR_BTN_DANGER_HOVER,
            border_width=1,
            border_color=COLOR_BTN_DANGER_BORDER,
            text_color=COLOR_BTN_DANGER_TEXT,
            corner_radius=8,
            command=self.confirm_disconnect
        )
        
        self.cancel_disconnect_btn = ctk.CTkButton(
            self.disconnect_cluster, 
            text="CANCEL", 
            width=70, 
            height=30, 
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLOR_BTN_SECONDARY_BG,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=COLOR_BTN_SECONDARY_BORDER,
            text_color=COLOR_TEXT_MUTED,
            corner_radius=8,
            command=self.hide_disconnect_confirm
        )
        
        # ----------------- Scrollable Message Flow Area -----------------
        self.scroll_area = ctk.CTkScrollableFrame(
            self.chat_frame,
            corner_radius=0,
            fg_color=COLOR_CANVAS,
            border_width=0
        )
        self.scroll_area.grid(row=1, column=0, sticky="nsew", padx=24, pady=0)
        self.scroll_area.grid_columnconfigure(0, weight=1)
        
        # 100% Invisible Scrollbar Track
        try:
            self.scroll_area._scrollbar.grid_forget()
            self.scroll_area.configure(
                scrollbar_button_color=COLOR_CANVAS,
                scrollbar_button_hover_color=COLOR_CANVAS,
                scrollbar_fg_color=COLOR_CANVAS
            )
            # High-precision 1-pixel granular scrolling for liquid-smooth trackpad motion
            self.scroll_area._parent_canvas.configure(yscrollincrement=1)
        except Exception:
            pass
            
        # Bindings for responsive layout resize
        self.scroll_area.bind("<Configure>", self.on_scroll_resize, add="+")
        
        # ----------------- Dynamic Auto-Expanding Input Dock -----------------
        self.input_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.input_container.grid(row=2, column=0, sticky="ew", padx=24, pady=(6, 14))
        self.input_container.grid_columnconfigure(0, weight=1)
        
        self.input_card = ctk.CTkFrame(
            self.input_container, 
            corner_radius=14,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_INPUT_BORDER
        )
        self.input_card.grid(row=0, column=0, sticky="ew")
        self.input_card.grid_columnconfigure(0, weight=1)
        self.input_card.grid_columnconfigure(1, weight=0)
        self.input_card.grid_rowconfigure(0, weight=1)
        
        # Dynamic Multi-line Input Box (Starts at 38px, expands up to 140px)
        self.input_textbox = ctk.CTkTextbox(
            self.input_card,
            height=INPUT_MIN_HEIGHT,
            wrap="word",
            font=(FONT_FAMILY, 13),
            fg_color="transparent",
            text_color=COLOR_TEXT_PRIMARY,
            border_width=0,
            activate_scrollbars=True
        )
        self.input_textbox.grid(row=0, column=0, sticky="ew", padx=(14, 6), pady=4)
        self.input_textbox.bind("<Return>", self.on_input_return)
        self.input_textbox.bind("<KeyRelease>", self.adjust_input_height)
        self.input_textbox.bind("<FocusIn>", lambda e: self.input_card.configure(border_color=COLOR_BORDER_FOCUS))
        self.input_textbox.bind("<FocusOut>", lambda e: self.input_card.configure(border_color=COLOR_INPUT_BORDER))
        
        # Action Button Cluster (Positioned Center-Right)
        self.action_cluster = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.action_cluster.grid(row=0, column=1, padx=(2, 10), pady=0, sticky="e")
        
        # Minimalist Upward Arrow Action Button ('↑') - Borderless, Monochrome
        self.send_btn = ctk.CTkButton(
            self.action_cluster, 
            text="↑", 
            width=32, 
            height=32, 
            font=(FONT_FAMILY, 15, "bold"), 
            fg_color=COLOR_BTN_PRIMARY_BG,
            hover_color=COLOR_BTN_PRIMARY_HOVER,
            border_width=0,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
            command=self.send_message
        )
        self.send_btn.pack()
        
        # '■' Minimalist Stop Square Icon - Borderless, Monochrome (Zero Red)
        self.stop_btn = ctk.CTkButton(
            self.action_cluster, 
            text="■", 
            width=32, 
            height=32, 
            font=(FONT_FAMILY, 12), 
            fg_color=COLOR_BTN_PRIMARY_BG,
            hover_color=COLOR_BTN_PRIMARY_HOVER,
            border_width=0,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
            command=self.stop_generation
        )
        
        # Global scroll wheel & trackpad interception: guarantees MacBook trackpad and mouse scrolling work across the chat
        try:
            self.bind_all("<TouchpadScroll>", self.on_touchpad_scroll)
            self.scroll_area._parent_canvas.bind("<TouchpadScroll>", self.on_touchpad_scroll)
            self.scroll_area.bind("<TouchpadScroll>", self.on_touchpad_scroll)
        except Exception:
            pass
        self.bind_all("<MouseWheel>", self.on_mouse_wheel)
        if "linux" in sys.platform:
            self.bind_all("<Button-4>", self.on_mouse_wheel)
            self.bind_all("<Button-5>", self.on_mouse_wheel)
        self.bind_all("<Prior>", self.on_page_up)
        self.bind_all("<Next>", self.on_page_down)
        
        # Click & drag anywhere on empty chat space to scroll
        self.scroll_area._parent_canvas.bind("<ButtonPress-1>", self.on_drag_start, add="+")
        self.scroll_area._parent_canvas.bind("<B1-Motion>", self.on_drag_motion, add="+")

    # ----------------- Keyboard, Resize & Smart Scroll -----------------
    def on_input_return(self, event):
        is_shift = (event.state & 0x1) != 0 or (event.state & 0x20000) != 0
        if not is_shift:
            self.send_message()
            return "break"
        # If shift is pressed, allow newline and adjust height
        self.after(10, self.adjust_input_height)
        return None

    def adjust_input_height(self, event=None):
        content = self.input_textbox.get("1.0", "end-1c")
        if not content:
            target_h = INPUT_MIN_HEIGHT
        else:
            lines = content.split("\n")
            w = max(200, self.input_textbox.winfo_width())
            chars_per_line = max(25, (w - 20) // 8)
            visual_lines = 0
            for l in lines:
                visual_lines += max(1, (len(l) // chars_per_line) + 1)
            calc_h = INPUT_MIN_HEIGHT + (visual_lines - 1) * INPUT_LINE_HEIGHT
            target_h = max(INPUT_MIN_HEIGHT, min(INPUT_MAX_HEIGHT, calc_h))
            
        if self.input_textbox.cget("height") != target_h:
            self.input_textbox.configure(height=target_h)

    def on_scroll_resize(self, event=None):
        try:
            self.scroll_area._scrollbar.grid_forget()
        except Exception:
            pass
            
        w = getattr(event, "width", None) or self.scroll_area.winfo_width()
        avail_w = max(260, w - 90)
        user_w = min(avail_w, 580)
        for item in self.bubble_items:
            try:
                widget = item[0]
                is_user = item[1]
                if is_user:
                    raw_text = item[2] if len(item) > 2 and item[2] is not None else widget.get_text()
                    widget.recalculate_user_width(user_w, raw_text)
                else:
                    widget.update_height()
            except Exception:
                pass
        try:
            self.scroll_area._parent_canvas.configure(scrollregion=self.scroll_area._parent_canvas.bbox("all"))
        except Exception:
            pass

    def on_touchpad_scroll(self, event):
        """Dedicated high-precision MacBook trackpad scrolling handler for Tk 9.0 on macOS."""
        if not self.chat_frame.winfo_ismapped():
            return

        try:
            widget_under_mouse = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            widget_under_mouse = None
            
        # If cursor is directly over the input textbox, only defer if textbox has multi-line overflow
        if widget_under_mouse:
            w_str = str(widget_under_mouse)
            tb_str = str(self.input_textbox)
            if widget_under_mouse == self.input_textbox or w_str.startswith(tb_str):
                try:
                    if self.input_textbox._textbox.yview() != (0.0, 1.0):
                        return
                except Exception:
                    pass

        # Decode Tk 9.0 packed delta (vertical delta in lower 16 bits)
        raw = getattr(event, "delta", 0)
        low = raw & 0xFFFF
        delta_y = low if low < 0x8000 else low - 0x10000
        
        if delta_y == 0:
            return

        # Scale delta with 1-pixel precision for liquid-smooth motion:
        if abs(delta_y) >= 60:
            scroll_pixels = -int(delta_y / 3)
        else:
            scroll_pixels = -int(delta_y * 1.5)
            
        if scroll_pixels == 0 and delta_y != 0:
            scroll_pixels = -1 if delta_y > 0 else 1

        if scroll_pixels < 0:
            # User scrolling UP: unpin auto-scroll immediately so stream doesn't yank view back down
            self.auto_scroll_pinned = False
            try:
                self.scroll_area._parent_canvas.yview_scroll(scroll_pixels, "units")
            except Exception:
                pass
        else:
            # User scrolling DOWN
            try:
                self.scroll_area._parent_canvas.yview_scroll(scroll_pixels, "units")
                cur_y = self.scroll_area._parent_canvas.yview()
                if cur_y[1] >= 0.98:
                    self.auto_scroll_pinned = True
            except Exception:
                pass

    def on_mouse_wheel(self, event):
        if not self.chat_frame.winfo_ismapped():
            return

        try:
            widget_under_mouse = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            widget_under_mouse = None
            
        # If cursor is directly over the input textbox, only defer if textbox has multi-line overflow
        if widget_under_mouse:
            w_str = str(widget_under_mouse)
            tb_str = str(self.input_textbox)
            if widget_under_mouse == self.input_textbox or w_str.startswith(tb_str):
                try:
                    if self.input_textbox._textbox.yview() != (0.0, 1.0):
                        return
                except Exception:
                    pass
                
        # Calculate scroll units based on platform
        delta = getattr(event, "delta", 0)
        if sys.platform == "darwin":
            if abs(delta) >= 60:
                scroll_pixels = -int(delta / 3)
            else:
                scroll_pixels = -int(delta * 1.5)
            if scroll_pixels == 0 and delta != 0:
                scroll_pixels = -2 if delta > 0 else 2
        elif sys.platform.startswith("win"):
            scroll_pixels = -int(delta / 4)
            if scroll_pixels == 0 and delta != 0:
                scroll_pixels = -2 if delta > 0 else 2
        else:
            if getattr(event, "num", None) == 4:
                scroll_pixels = -16
            elif getattr(event, "num", None) == 5:
                scroll_pixels = 16
            else:
                scroll_pixels = -int(delta / 4) if delta != 0 else 0
                
        if scroll_pixels == 0:
            return

        if scroll_pixels < 0:
            # Scrolling UP: user intentionally viewing older history -> unpin auto-scroll immediately
            self.auto_scroll_pinned = False
            try:
                self.scroll_area._parent_canvas.yview_scroll(scroll_pixels, "units")
            except Exception:
                pass
        else:
            # Scrolling DOWN: move view and re-pin auto-scroll if user scrolled all the way to bottom
            try:
                self.scroll_area._parent_canvas.yview_scroll(scroll_pixels, "units")
                cur_y = self.scroll_area._parent_canvas.yview()
                if cur_y[1] >= 0.98:
                    self.auto_scroll_pinned = True
            except Exception:
                pass

    def scroll_to_bottom(self, force=False):
        if not force and not self.auto_scroll_pinned:
            return
        try:
            self.scroll_area.update_idletasks()
            self.scroll_area._parent_canvas.configure(
                scrollregion=self.scroll_area._parent_canvas.bbox("all")
            )
            self.scroll_area._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def on_page_up(self, event=None):
        if not self.chat_frame.winfo_ismapped():
            return
        self.auto_scroll_pinned = False
        try:
            self.scroll_area._parent_canvas.yview_scroll(-6, "units")
        except Exception:
            pass

    def on_page_down(self, event=None):
        if not self.chat_frame.winfo_ismapped():
            return
        try:
            self.scroll_area._parent_canvas.yview_scroll(6, "units")
            cur_y = self.scroll_area._parent_canvas.yview()
            if cur_y[1] >= 0.98:
                self.auto_scroll_pinned = True
        except Exception:
            pass

    def on_drag_start(self, event):
        self.auto_scroll_pinned = False
        try:
            self.scroll_area._parent_canvas.scan_mark(event.x, event.y)
        except Exception:
            pass

    def on_drag_motion(self, event):
        self.auto_scroll_pinned = False
        try:
            self.scroll_area._parent_canvas.scan_dragto(event.x, event.y, gain=1)
        except Exception:
            pass

    # ----------------- Disconnect Confirmation Feature -----------------
    def show_disconnect_confirm(self):
        self.is_confirming_disconnect = True
        self.disconnect_btn.pack_forget()
        self.cancel_disconnect_btn.pack(side="left", padx=(0, 6))
        self.confirm_disconnect_btn.pack(side="left")
        
        if self.disconnect_reset_timer:
            self.after_cancel(self.disconnect_reset_timer)
        self.disconnect_reset_timer = self.after(6000, self.hide_disconnect_confirm)

    def hide_disconnect_confirm(self):
        self.is_confirming_disconnect = False
        self.confirm_disconnect_btn.pack_forget()
        self.cancel_disconnect_btn.pack_forget()
        self.disconnect_btn.pack(side="left")
        if self.disconnect_reset_timer:
            self.after_cancel(self.disconnect_reset_timer)
            self.disconnect_reset_timer = None

    def confirm_disconnect(self):
        self.hide_disconnect_confirm()
        self.on_change_model_click()

    # ----------------- Fluid Micro-Animations -----------------
    def animate_loading(self):
        if not self.is_loading:
            return
        dots = "." * (self.anim_step % 4)
        pad = " " * (3 - (self.anim_step % 4))
        self.status_label.configure(text=f"ALLOCATING UNIFIED MEMORY {dots}{pad}")
        self.anim_step += 1
        self.after(300, self.animate_loading)

    def animate_thinking(self):
        if not self.is_thinking:
            return
        dots = "." * ((self.anim_step % 3) + 1)
        if self.current_thinking_label:
            try:
                self.current_thinking_label.configure(text=f"thinking{dots}")
            except Exception:
                pass
        self.anim_step += 1
        self.after(300, self.animate_thinking)

    def update_context_gauge(self, tokens_used=None):
        if tokens_used is not None:
            self.current_context_tokens = tokens_used
        pct = 0.0
        if getattr(self, "context_size", 0) > 0:
            pct = (self.current_context_tokens / self.context_size) * 100.0
        pct = min(100.0, max(0.0, pct))
        
        if not hasattr(self, "context_gauge") or self.context_gauge is None:
            return
            
        try:
            self.context_gauge.delete("all")
            cx, cy, r = 18, 18, 11
            w = 2.5
            # Background circular track ring
            self.context_gauge.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#1E1E1E", width=w)
            if pct > 0:
                extent = -max(1, int(360 * (pct / 100.0)))
                color = "#B86666" if pct >= 90 else "#8E95A3"
                self.context_gauge.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=extent, style="arc", outline=color, width=w)
        except Exception:
            pass

    # ----------------- Reasoning Toggle Logic -----------------
    def on_setup_reasoning_toggle(self):
        self.reasoning_enabled = bool(self.setup_reasoning_switch.get())
        self.update_reasoning_button_ui()

    def toggle_reasoning(self):
        self.reasoning_enabled = not self.reasoning_enabled
        self.update_reasoning_button_ui()
        if self.setup_reasoning_switch:
            if self.reasoning_enabled:
                self.setup_reasoning_switch.select()
            else:
                self.setup_reasoning_switch.deselect()

    def update_reasoning_button_ui(self):
        if self.reasoning_enabled:
            self.reasoning_btn.configure(
                text="REASONING: ON", 
                fg_color=COLOR_REASONING_ON_BG, 
                hover_color=COLOR_REASONING_ON_HOVER,
                border_color=COLOR_REASONING_ON_BORDER,
                text_color=COLOR_REASONING_ON_TEXT
            )
        else:
            self.reasoning_btn.configure(
                text="REASONING: OFF", 
                fg_color=COLOR_REASONING_OFF_BG, 
                hover_color=COLOR_REASONING_OFF_HOVER,
                border_color=COLOR_REASONING_OFF_BORDER,
                text_color=COLOR_REASONING_OFF_TEXT
            )

    # ----------------- Model Lifecycle -----------------
    def on_load_click(self):
        model_name = self.model_var.get()
        model_path = os.path.join(get_models_dir(), model_name)
        try:
            self.context_size = int(self.context_var.get().strip())
        except:
            self.context_size = 4096
            
        self.load_btn.configure(state="disabled")
        self.is_loading = True
        self.anim_step = 0
        self.animate_loading()
        self.task_queue.put(("load", (model_name, model_path)))

    def on_change_model_click(self):
        self.task_queue.put(("unload", None))
        self.chat_frame.grid_forget()
        self.setup_container.grid(row=0, column=0, sticky="nsew")
        self.load_btn.configure(state="normal")
        self.status_label.configure(text="MEMORY PURGED (0.00 GB ALLOCATED)", text_color=COLOR_TEXT_MUTED)
        self.update_context_gauge(0)

    # ----------------- Asymmetric Chat Rendering -----------------
    def add_user_message_bubble(self, text):
        container = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        container.pack(fill="x", padx=12, pady=(8, 6))
        container.grid_columnconfigure(0, weight=1)
        
        bubble = ctk.CTkFrame(
            container,
            corner_radius=16,
            fg_color=COLOR_USER_BUBBLE,
            border_width=1,
            border_color=COLOR_USER_BORDER
        )
        bubble.pack(anchor="e", padx=(80, 8))
        
        header = ctk.CTkLabel(
            bubble,
            text="YOU",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLOR_TEXT_MUTED
        )
        header.pack(anchor="e", padx=16, pady=(10, 2))
        
        wrap_w = min(max(240, self.scroll_area.winfo_width() - 120), 580)
        msg_text = SelectableMessageText(
            bubble,
            bg=COLOR_USER_BUBBLE,
            fg=COLOR_TEXT_PRIMARY,
            app=self
        )
        msg_text.recalculate_user_width(wrap_w, text)
        msg_text.pack(anchor="e", padx=16, pady=(0, 12))
        msg_text.set_text(text)
        self.bubble_items.append((msg_text, True, text))

    def add_assistant_direct_typography(self):
        container = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        container.pack(fill="x", padx=12, pady=(6, 14))
        container.grid_columnconfigure(0, weight=1)
        
        ai_block = ctk.CTkFrame(container, fg_color="transparent", border_width=0)
        ai_block.pack(fill="x", padx=(16, 60))
        
        header = ctk.CTkLabel(
            ai_block,
            text="ASSISTANT",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        header.pack(fill="x", pady=(8, 3))
        
        # 'thinking..' label with moving periods, right under ASSISTANT
        self.current_thinking_label = ctk.CTkLabel(
            ai_block,
            text="thinking.",
            font=(FONT_FAMILY, 12, "italic"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        self.current_thinking_label.pack(fill="x", pady=(2, 6))
        
        # Output text widget (packed as soon as first token output arrives)
        msg_text = SelectableMessageText(
            ai_block,
            bg=COLOR_CANVAS,
            fg=COLOR_TEXT_PRIMARY,
            app=self
        )
        
        # Footer with stats and copy icon (packed as soon as first token output arrives)
        footer = ctk.CTkFrame(ai_block, fg_color="transparent")
        
        stats_lbl = ctk.CTkLabel(
            footer,
            text="",
            font=(FONT_FAMILY, 10),
            text_color=COLOR_STATS_TEXT,
            anchor="w"
        )
        stats_lbl.pack(side="left", padx=(0, 4))
        
        copy_btn = ctk.CTkButton(
            footer,
            text="⧉",
            width=20,
            height=20,
            font=(FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color="#141414",
            text_color=COLOR_STATS_TEXT,
            corner_radius=4
        )
        
        def on_copy_click(btn=copy_btn, widget=msg_text):
            txt = widget.get_text()
            if txt:
                self.clipboard_clear()
                self.clipboard_append(txt)
                btn.configure(text="✓", text_color=COLOR_STATUS_ACTIVE)
                self.after(1200, lambda: btn.configure(text="⧉", text_color=COLOR_STATS_TEXT))
                
        copy_btn.configure(command=on_copy_click)
        
        for w in (footer, stats_lbl, copy_btn, self.current_thinking_label):
            try:
                w.bind("<TouchpadScroll>", self.on_touchpad_scroll)
                w.bind("<MouseWheel>", self.on_mouse_wheel)
            except Exception:
                pass
                
        self.current_asst_label = msg_text
        self.current_asst_text = msg_text
        self.current_asst_footer = footer
        self.current_asst_stats = stats_lbl
        self.current_asst_copy_btn = copy_btn
        self.bubble_items.append((msg_text, False, None))
        
        # Start thinking animation with moving periods
        self.is_thinking = True
        self.anim_step = 0
        self.animate_thinking()

    def add_system_pill(self, text):
        pill_frame = ctk.CTkFrame(
            self.scroll_area,
            corner_radius=10,
            fg_color=COLOR_SYSTEM_PILL,
            border_width=1,
            border_color=COLOR_SYSTEM_BORDER
        )
        pill_frame.pack(anchor="center", pady=(10, 8))
        lbl = ctk.CTkLabel(
            pill_frame,
            text=text,
            font=(FONT_FAMILY, 11),
            text_color=COLOR_TEXT_MUTED
        )
        lbl.pack(padx=14, pady=4)

    # ----------------- Inference Orchestration -----------------
    def send_message(self):
        if self.is_generating:
            return
        user_input = self.input_textbox.get("1.0", "end").strip()
        if not user_input:
            return
            
        # Reset input box content and collapse back to compact single-line height
        self.input_textbox.delete("1.0", "end")
        self.input_textbox.configure(height=INPUT_MIN_HEIGHT)
        self.is_generating = True
        
        # Swap '↑' send arrow button to '■' stop square
        self.send_btn.pack_forget()
        self.stop_btn.pack()
        
        self.add_user_message_bubble(user_input)
        self.messages.append({"role": "user", "content": user_input})
        
        # Immediate prompt token estimate on context gauge
        approx_tokens = sum(len(m["content"].split()) * 4 // 3 for m in self.messages)
        self.update_context_gauge(approx_tokens)
        
        # Prepare direct AI typography flow (shows 'thinking..' with moving periods)
        self.add_assistant_direct_typography()
        
        # Always re-pin auto-scroll and snap to bottom when sending a new prompt
        self.auto_scroll_pinned = True
        self.scroll_to_bottom(force=True)
        
        self.task_queue.put(("generate", (list(self.messages), self.context_size, self.reasoning_enabled)))

    def stop_generation(self):
        if self.is_generating:
            if self.is_thinking:
                self.is_thinking = False
                if self.current_thinking_label:
                    self.current_thinking_label.pack_forget()
                if self.current_asst_text:
                    self.current_asst_text.pack(fill="x", pady=(0, 4))
                if self.current_asst_footer:
                    self.current_asst_footer.pack(fill="x", pady=(2, 0))
            self.worker.stop_event.set()

    def poll_worker(self):
        should_scroll = False
        while not self.result_queue.empty():
            msg_type, data = self.result_queue.get_nowait()
            if msg_type == "load_success":
                self.is_loading = False
                model_name, duration = data
                self.setup_container.grid_forget()
                self.chat_frame.grid(row=0, column=0, sticky="nsew")
                self.update_reasoning_button_ui()
                self.model_info_label.configure(text=f"{model_name.upper()}  •  CTX {self.context_size}")
                self.current_context_tokens = 0
                self.update_context_gauge(0)
                self.messages = []
                self.bubble_items = []
                for widget in self.scroll_area.winfo_children():
                    widget.destroy()
                self.auto_scroll_pinned = True
                self.scroll_to_bottom(force=True)
                self.input_textbox.focus()
            elif msg_type == "load_error":
                self.is_loading = False
                self.status_label.configure(text=f"LOAD ERROR: {data}", text_color=COLOR_TEXT_ERROR)
                self.load_btn.configure(state="normal")
            elif msg_type == "context_update":
                self.update_context_gauge(data)
            elif msg_type == "thought_start":
                self.anim_step = 0
                should_scroll = True
            elif msg_type == "thought_chunk":
                if len(data) > 2 and data[2] is not None:
                    self.update_context_gauge(data[2])
            elif msg_type == "thought_end":
                should_scroll = True
            elif msg_type == "answer_chunk":
                chunk = data[0]
                tps = data[1]
                token_count = data[2]
                total_ctx = data[3] if len(data) > 3 else None
                
                # As soon as AI begins outputting, remove thinking label and display output widgets
                if self.is_thinking:
                    self.is_thinking = False
                    if self.current_thinking_label:
                        self.current_thinking_label.pack_forget()
                    if self.current_asst_text:
                        self.current_asst_text.pack(fill="x", pady=(0, 4))
                    if self.current_asst_footer:
                        self.current_asst_footer.pack(fill="x", pady=(2, 0))
                        
                if self.current_asst_text:
                    self.current_asst_text.append_text(chunk)
                    if self.is_generating:
                        should_scroll = True
                if self.current_asst_stats and tps > 0:
                    self.current_asst_stats.configure(text=f"{tps:.1f} t/s  •  {token_count} tokens")
                if self.current_asst_copy_btn:
                    self.current_asst_copy_btn.pack(side="left")
                if total_ctx is not None:
                    self.update_context_gauge(total_ctx)
            elif msg_type == "gen_done":
                final_answer = data[0]
                count = data[1]
                duration = data[2]
                final_tps = data[3]
                was_stopped = data[4]
                final_ctx = data[5] if len(data) > 5 else None
                self.messages.append({"role": "assistant", "content": final_answer})
                
                if self.is_thinking:
                    self.is_thinking = False
                    if self.current_thinking_label:
                        self.current_thinking_label.pack_forget()
                    if self.current_asst_text:
                        self.current_asst_text.pack(fill="x", pady=(0, 4))
                    if self.current_asst_footer:
                        self.current_asst_footer.pack(fill="x", pady=(2, 0))
                        
                if self.current_asst_text:
                    if self.current_asst_text.get_text() != final_answer:
                        self.current_asst_text.set_text(final_answer)
                    else:
                        self.current_asst_text.update_height()
                if self.current_asst_stats:
                    if was_stopped:
                        self.current_asst_stats.configure(text=f"{final_tps:.1f} t/s  •  {count} tokens  •  aborted")
                    else:
                        self.current_asst_stats.configure(text=f"{final_tps:.1f} t/s  •  {count} tokens in {duration:.2f}s")
                if self.current_asst_copy_btn:
                    self.current_asst_copy_btn.pack(side="left")
                if final_ctx is not None:
                    self.update_context_gauge(final_ctx)
                    
                self.is_generating = False
                self.stop_btn.pack_forget()
                self.send_btn.pack()
                should_scroll = True
                self.input_textbox.focus()
            elif msg_type == "gen_error":
                if self.is_thinking:
                    self.is_thinking = False
                    if self.current_thinking_label:
                        self.current_thinking_label.pack_forget()
                    if self.current_asst_text:
                        self.current_asst_text.pack(fill="x", pady=(0, 4))
                if self.current_asst_text:
                    self.current_asst_text.append_text(f"\n[Error: {data}]")
                self.is_generating = False
                self.stop_btn.pack_forget()
                self.send_btn.pack()
                should_scroll = True
                self.input_textbox.focus()
                
        if should_scroll:
            self.scroll_to_bottom()
            
        self.after(20, self.poll_worker)

if __name__ == "__main__":
    app = App()
    app.mainloop()
