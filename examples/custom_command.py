"""Example: Using Remi programmatically to evaluate custom speech commands."""
from remi.core.config import load
from remi.tools.router import run

def main():
    cfg = load()
    
    # Simulate transcribed user commands in English and Hinglish
    commands = [
        "youtube lofi beats",
        "open github",
        "scroll down",
        "what time is it",
        "tab band karo",
    ]
    
    print("Testing Remi command router:")
    for cmd in commands:
        outcome = run(cmd, cfg)
        print(f"  Command : '{cmd}'")
        print(f"    OK    : {outcome.ok}")
        print(f"    Spoken: {outcome.spoken}")
        print(f"    Detail: {outcome.detail}\n")

if __name__ == "__main__":
    main()
