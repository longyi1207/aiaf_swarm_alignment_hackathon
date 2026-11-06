#!/usr/bin/env bash
# Stop a supervised job by name: supervisor first (so it does not restart the job), then the job.
#   bash scripts/pod_stop.sh <name> <swarmtom-args-substring>
name=$1; pat=$2; me=$$
for pid in $(pgrep -f "pod_supervise.sh $name "); do [ "$pid" != "$me" ] && kill "$pid"; done
sleep 1
for pid in $(pgrep -f "bin/swarmtom .*$pat"); do [ "$pid" != "$me" ] && kill "$pid"; done
for i in $(seq 1 60); do pgrep -f "bin/swarmtom .*$pat" >/dev/null || break; sleep 1; done
pgrep -fa "bin/swarmtom" || echo "no swarmtom processes"
