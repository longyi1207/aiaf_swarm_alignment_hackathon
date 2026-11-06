#!/usr/bin/env bash
# Generate a run's worlds in parallel into a staging dir, then move finished ones into place (skipping any the
# runner already created). Worlds are deterministic given their spec, so this only saves wall-clock time.
#   bash scripts/pod_pregen_worlds.sh <run_dir> <seed>... -- <k>... -- <harm>... -- <comm>...
run=$1; shift
seeds=(); ks=(); harms=(); comms=(); cur=seeds
for a in "$@"; do
  if [ "$a" = "--" ]; then case $cur in seeds) cur=ks;; ks) cur=harms;; harms) cur=comms;; esac; continue; fi
  eval "$cur+=(\"$a\")"
done
stage=/workspace/wstage/$(basename "$run"); rm -rf "$stage"; mkdir -p "$stage" "$run/worlds"
cd /workspace/repo
for s in "${seeds[@]}"; do for k in "${ks[@]}"; do for h in "${harms[@]}"; do for c in "${comms[@]}"; do
  HF_HUB_OFFLINE=1 /root/venv/bin/swarmtom gen-world --seed "$s" --k-evidence "$k" --harm "$h" --communication "$c" --out "$stage" > /dev/null 2>&1 &
done; done; done; done
wait
for w in "$stage"/*; do n=$(basename "$w")
  if [ -f "$w/ground_truth.json" ] && [ ! -e "$run/worlds/$n" ]; then mv "$w" "$run/worlds/$n" && echo "moved $n"; else echo "skip $n"; fi
done
