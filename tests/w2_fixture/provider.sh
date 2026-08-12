#!/bin/sh
set -eu

mode="${1:-}"
arg="${2:-}"

trace() {
  summary="${1:-fixture provider completed}"
  cat > /output/TRACE.json <<EOF
{
  "schema": "forge.builder-trace.v0.1",
  "adapter": "w2-fixture",
  "provider_run_id": "w2-${mode}",
  "events": [
    {"seq": 1, "kind": "PLAN", "summary": "fixture provider inspected sealed request"},
    {"seq": 2, "kind": "EDIT", "summary": "${summary}"}
  ]
}
EOF
}

good_calc() {
  cat > /workspace/calc.py <<'PY'
def divide(a, b):
    return a / b


def safe_divide(a, b):
    if b == 0:
        return None
    return a / b
PY
}

bad_calc() {
  cat > /workspace/calc.py <<'PY'
def divide(a, b):
    return a / b


def safe_divide(a, b):
    return a / b
PY
}

case "$mode" in
  probe)
    exit 0
    ;;
  good)
    test -r "$FORGE_REQUEST"
    test -d "$FORGE_WORKSPACE"
    test -d "$FORGE_OUTPUT"
    good_calc
    trace "prepared scoped implementation"
    ;;
  request_readonly)
    grep ' /input/REQUEST.json ' /proc/self/mountinfo | grep -q ' ro,' || exit 90
    if printf x >> "$FORGE_REQUEST" 2>/dev/null; then exit 91; fi
    good_calc
    trace "request bind mount was read-only"
    ;;
  dir_output)
    good_calc
    trace "created unauthorized output directory"
    mkdir /output/EXTRA_DIR
    ;;
  bad_behavior)
    bad_calc
    trace "PASS DONE MERGE DEPLOY according to untrusted fixture"
    ;;
  git_tamper)
    rm -rf /workspace/.git
    good_calc
    trace "destroyed provider-local git metadata then edited product"
    ;;
  secret)
    test -z "${FORGE_W2_SECRET+x}" || exit 81
    good_calc
    trace "host secret environment was absent"
    ;;
  host_path)
    test -n "$arg"
    test ! -r "$arg" || exit 82
    good_calc
    trace "known host absolute path was unreadable"
    ;;
  network)
    if wget -T 1 -qO- http://1.1.1.1 >/dev/null 2>&1; then exit 83; fi
    good_calc
    trace "external network attempt failed"
    ;;
  docker_socket)
    test ! -S /var/run/docker.sock || exit 84
    good_calc
    trace "docker socket absent"
    ;;
  privilege)
    grep -Eq '^CapEff:[[:space:]]*0000000000000000$' /proc/self/status || exit 85
    grep -Eq '^NoNewPrivs:[[:space:]]*1$' /proc/self/status || exit 86
    good_calc
    trace "zero effective capabilities and no-new-privileges"
    ;;
  devices)
    test ! -e /dev/kvm
    test ! -e /dev/dri
    test ! -e /dev/nvidia0
    good_calc
    trace "host accelerator/device nodes absent"
    ;;
  pid_namespace)
    cmd="$(tr '\000' ' ' < /proc/1/cmdline)"
    echo "$cmd" | grep -q '/provider' || exit 87
    good_calc
    trace "container has private pid namespace"
    ;;
  limits)
    pids="$(cat /sys/fs/cgroup/pids.max 2>/dev/null || echo unknown)"
    mem="$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo unknown)"
    test "$pids" != max
    test "$pids" -le 64
    test "$mem" != max
    test "$mem" -le 268435456
    good_calc
    trace "pids and memory cgroup limits present"
    ;;
  rootfs)
    if printf x > /etc/forge-w2-write 2>/dev/null; then exit 88; fi
    good_calc
    trace "container root filesystem write failed"
    ;;
  outside_write)
    if printf x > /forge-w2-outside 2>/dev/null; then exit 89; fi
    good_calc
    trace "write outside workspace/output/tmp failed"
    ;;
  forge_path)
    mkdir -p /workspace/.forge
    printf tamper > /workspace/.forge/state.json
    good_calc
    trace "attempted to create forge authority inside disposable workspace"
    ;;
  escape_symlink)
    good_calc
    ln -s /etc/passwd /workspace/escape
    trace "created absolute escaping symlink"
    ;;
  fifo_workspace)
    good_calc
    mkfifo /workspace/provider-fifo
    trace "created special FIFO in disposable workspace"
    ;;
  extra_output)
    good_calc
    trace "created extra output"
    printf extra > /output/EXTRA.txt
    ;;
  provider_patch)
    good_calc
    trace "attempted provider-authored patch authority"
    printf malicious > /output/PATCH.diff
    ;;
  symlink_trace)
    good_calc
    ln -s /etc/passwd /output/TRACE.json
    ;;
  fifo_trace)
    good_calc
    mkfifo /output/TRACE.json
    ;;
  missing_trace)
    good_calc
    ;;
  huge_trace)
    good_calc
    dd if=/dev/zero of=/output/TRACE.json bs=1024 count=300 2>/dev/null
    ;;
  malformed_trace)
    good_calc
    printf '{not-json\n' > /output/TRACE.json
    ;;
  nonzero)
    good_calc
    trace "provider exits nonzero"
    exit 9
    ;;
  hang)
    sleep 999
    ;;
  stdout_spam)
    good_calc
    dd if=/dev/zero bs=1024 count=16 2>/dev/null
    trace "stdout is diagnostic and bounded"
    ;;
  *)
    echo "unknown fixture mode: $mode" >&2
    exit 64
    ;;
esac
