#!/usr/bin/env bash
# One-shot setup: python deps + free 0.5B model (491 MB). Needs ~1 GB RAM. No paid service, no API key.
set -e
python3 -m pip install --quiet llama-cpp-python pytest \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
mkdir -p models
[ -f models/qwen.gguf ] || curl -L -o models/qwen.gguf \
  https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
echo "Now run:  export FORGE_MODEL=\$PWD/models/qwen.gguf"
echo "  python3 -m pytest -q tests"
echo "  python3 -m forgeai chat --agent runs/hr/agent.json -q 'How many days of sick leave do I get?'"
echo "  python3 -m forgeai chat --agent runs/procurement/agent.json -q 'What is the unit price of part MP-1003?'"
echo "  python3 -m forgeai build --brief \"\$(cat demo_inputs/hr/brief.txt)\" --docs demo_inputs/hr/docs --out runs/my_hr --unattended"
