"""Settings shared by all scripts. Change the model here."""

# Name of the model exactly as shown by `ollama list`.
MODEL = "qwen3:1.7b"

# The four labels Percy uses.
LABELS = ["urgent", "action", "fyi", "noise"]

# Mail bodies longer than this are cut, so the prompt fits into the model's memory.
MAX_BODY_CHARS = 3000
