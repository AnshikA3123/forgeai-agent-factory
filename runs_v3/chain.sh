cd /downloads/forgeai-build; export FORGE_MODEL=/tmp/iso/repo/models/qwen.gguf PYTHONUNBUFFERED=1
run(){ n=$1; docs=$2; brief=$3; python3 -m forgeai build --brief "$(cat $brief)" --docs $docs --out runs_v3/$n --unattended > /tmp/v3_$n.log 2>&1; echo FINISHED >> /tmp/v3_$n.log; }
[ -f runs_v3/procurement/report.md ] || run procurement demo_inputs/procurement/docs demo_inputs/procurement/brief.txt
[ -f runs_v3/hr/report.md ] || run hr demo_inputs/hr/docs demo_inputs/hr/brief.txt
echo ALLDONE > /tmp/chain3.done
