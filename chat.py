import os
import sys
import glob

import mlx.core as mx
from mlx_lm import load, stream_generate

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

def main():
    print("\n--- MLX MTP Fast Terminal Chat ---\n")
    models = get_models()
    if not models:
        print(f"No models found in {get_models_dir()}")
        sys.exit(1)
        
    print("Available Models:")
    for i, m in enumerate(models):
        print(f"[{i+1}] {m}")
        
    choice = -1
    while not (0 <= choice < len(models)):
        try:
            choice = int(input("\nSelect model number: ")) - 1
        except:
            pass
            
    model_name = models[choice]
    model_path = os.path.join(get_models_dir(), model_name)
    
    context_size = 0
    while context_size <= 0:
        try:
            context_size = int(input("Enter max context window (e.g. 2048, 4096): "))
        except:
            pass
            
    print(f"\nLoading {model_name} with context {context_size} (this may take a moment)...")
    
    try:
        model, tokenizer = load(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
        
    print("\nModel loaded successfully! Type 'quit' or 'exit' to stop.\n")
    print("-" * 50)
    
    messages = []
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.strip().lower() in ['quit', 'exit']:
                break
                
            messages.append({"role": "user", "content": user_input})
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            
            print("\nModel: ", end="", flush=True)
            
            response = ""
            for resp in stream_generate(model, tokenizer, prompt=prompt, max_tokens=context_size):
                text_chunk = resp.text
                print(text_chunk, end="", flush=True)
                response += text_chunk
            print()
            
            messages.append({"role": "assistant", "content": response.strip()})
            
        except KeyboardInterrupt:
            print("\nChat interrupted. Type 'quit' to exit.")
        except EOFError:
            break

if __name__ == "__main__":
    main()
