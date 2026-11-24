cd /downloads/forgeai-build; export FORGE_MODEL=/tmp/iso/repo/models/qwen.gguf PYTHONUNBUFFERED=1
run(){ n=$1; docs=$2; brief=$3; python3 -m forgeai build --brief "$(cat $brief)" --docs $docs --out runs_v2/$n --unattended > /tmp/v2_$n.log 2>&1; echo FINISHED >> /tmp/v2_$n.log; }

[ -f runs_v2/procurement/report.md ] || run procurement demo_inputs/procurement/docs demo_inputs/procurement/brief.txt

echo ALLDONE > /tmp/chain.done
