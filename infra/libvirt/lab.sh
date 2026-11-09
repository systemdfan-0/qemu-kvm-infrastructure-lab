#!/usr/bin/env bash
# Reference host-side provisioning for the QEMU/KVM Infrastructure Lab.
#
#   lab.sh [--dry-run] networks   define and start the five lab networks
#   lab.sh [--dry-run] vms        create the six guests from a Debian 13 cloud image
#   lab.sh [--dry-run] up         networks + vms
#   lab.sh status                 read-only: show lab-* networks and domains
#   lab.sh [--dry-run] destroy    stop and delete ONLY objects named lab-* (asks to confirm)
#
# Safety properties:
#   * Every object it touches is named lab-* (domains/networks) or labbr-* (bridges).
#   * Existing objects are never modified; they are skipped.
#   * --dry-run prints every mutating command and runs nothing that changes state.
#   * No password is created. Guests accept only the SSH public key you supply.
set -euo pipefail

export LIBVIRT_DEFAULT_URI="${LIBVIRT_DEFAULT_URI:-qemu:///system}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="${LAB_DIR:-/var/lib/libvirt/images/qemu-kvm-lab}"   # must be writable by you, readable by libvirt-qemu
LAB_BASE_IMAGE="${LAB_BASE_IMAGE:-}"                          # path to a verified Debian 13 genericcloud qcow2
LAB_SSH_PUBKEY="${LAB_SSH_PUBKEY:-}"                          # path to a PUBLIC key file (*.pub)
LAB_RAM_MIB="${LAB_RAM_MIB:-512}"
LAB_DISK_GIB="${LAB_DISK_GIB:-4}"
LAB_OS_VARIANT="${LAB_OS_VARIANT:-debian13}"
LAB_ADMIN_USER="${LAB_ADMIN_USER:-debian}"
DRY_RUN=0

# name|management MAC (synthetic)|management IP|segments in NIC order after the management NIC
VMS=(
  "lab-edge|52:54:00:ab:cd:11|192.168.150.11|lan dmz wan"
  "lab-isp-router|52:54:00:ab:cd:12|192.168.150.12|wan isp"
  "lab-lan-a|52:54:00:ab:cd:21|192.168.150.21|lan"
  "lab-lan-b|52:54:00:ab:cd:22|192.168.150.22|lan"
  "lab-dmz-web|52:54:00:ab:cd:31|192.168.150.31|dmz"
  "lab-isp-client|52:54:00:ab:cd:41|192.168.150.41|isp"
)
NETWORKS=(lab-mgmt lab-lan lab-dmz lab-wan lab-isp)

die() { echo "error: $*" >&2; exit 1; }

# Print-or-run for state-changing commands.
run() {
  if [ "$DRY_RUN" = 1 ]; then
    printf '[dry-run]'; printf ' %q' "$@"; printf '\n'
  else
    "$@"
  fi
}

net_exists() { virsh net-info "$1" >/dev/null 2>&1; }
dom_exists() { virsh dominfo "$1" >/dev/null 2>&1; }

cmd_networks() {
  local n
  for n in "${NETWORKS[@]}"; do
    if net_exists "$n"; then
      echo "skip: network $n already exists"
      continue
    fi
    run virsh net-define "$HERE/networks/$n.xml"
    run virsh net-start "$n"
    run virsh net-autostart "$n"
  done
}

write_cloud_init() { # name mac ip dir
  local name=$1 mac=$2 ip=$3 dir=$4 pub
  pub="$(cat "$LAB_SSH_PUBKEY")"
  case "$pub" in
    ssh-*|ecdsa-*|sk-*) ;;
    *) die "$LAB_SSH_PUBKEY does not look like a public key" ;;
  esac
  mkdir -p "$dir"
  cat >"$dir/user-data" <<EOF
#cloud-config
ssh_pwauth: false
disable_root: true
users:
  - name: $LAB_ADMIN_USER
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
    ssh_authorized_keys:
      - $pub
EOF
  cat >"$dir/meta-data" <<EOF
instance-id: $name
local-hostname: $name
EOF
  # Static management address, deliberately WITHOUT a default route: the lab must not
  # reach the Internet. bootstrap.yml adds a temporary runtime route for package installs.
  cat >"$dir/network-config" <<EOF
version: 2
ethernets:
  mgmt:
    match:
      macaddress: "$mac"
    addresses: ["$ip/24"]
    nameservers:
      addresses: [192.168.150.1]
EOF
}

cmd_vms() {
  [ -n "$LAB_BASE_IMAGE" ] || die "set LAB_BASE_IMAGE to a verified Debian 13 genericcloud qcow2"
  [ -n "$LAB_SSH_PUBKEY" ] || die "set LAB_SSH_PUBKEY to your public key file"
  [ -r "$LAB_BASE_IMAGE" ] || die "cannot read $LAB_BASE_IMAGE"
  [ -r "$LAB_SSH_PUBKEY" ] || die "cannot read $LAB_SSH_PUBKEY"
  local row name mac ip segs disk args seg ci
  for row in "${VMS[@]}"; do
    IFS='|' read -r name mac ip segs <<<"$row"
    if dom_exists "$name"; then
      echo "skip: domain $name already exists"
      continue
    fi
    disk="$LAB_DIR/$name.qcow2"
    ci="$LAB_DIR/cloud-init/$name"
    run mkdir -p "$LAB_DIR"
    run qemu-img create -q -f qcow2 -b "$LAB_BASE_IMAGE" -F qcow2 "$disk" "${LAB_DISK_GIB}G"
    if [ "$DRY_RUN" = 1 ]; then
      echo "[dry-run] write cloud-init user-data/meta-data/network-config to $ci"
    else
      write_cloud_init "$name" "$mac" "$ip" "$ci"
    fi
    args=(--network "network=lab-mgmt,model=virtio,mac=$mac")
    for seg in $segs; do
      args+=(--network "network=lab-$seg,model=virtio")
    done
    run virt-install --name "$name" --memory "$LAB_RAM_MIB" --vcpus 1 \
      --os-variant "$LAB_OS_VARIANT" --import --noautoconsole \
      --disk "path=$disk,bus=virtio" "${args[@]}" \
      --cloud-init "user-data=$ci/user-data,meta-data=$ci/meta-data,network-config=$ci/network-config" \
      --channel unix,target_type=virtio,name=org.qemu.guest_agent.0
  done
}

cmd_status() {
  echo "== networks"; virsh net-list --all | grep -E 'Name|Имя|lab-' || true
  echo "== domains";  virsh list --all      | grep -E 'Name|Имя|lab-' || true
}

cmd_destroy() {
  local row name mac ip segs n answer
  if [ "$DRY_RUN" != 1 ]; then
    read -r -p "Delete lab-* domains, their disks and lab-* networks? Type 'yes': " answer
    [ "$answer" = yes ] || die "aborted"
  fi
  for row in "${VMS[@]}"; do
    IFS='|' read -r name mac ip segs <<<"$row"
    if dom_exists "$name"; then
      run virsh destroy "$name" || true
      run virsh undefine "$name"
      run rm -f -- "$LAB_DIR/$name.qcow2"
      run rm -rf -- "$LAB_DIR/cloud-init/$name"
    fi
  done
  for n in "${NETWORKS[@]}"; do
    if net_exists "$n"; then
      run virsh net-destroy "$n" || true
      run virsh net-undefine "$n"
    fi
  done
}

main() {
  if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=1; shift; fi
  case "${1:-}" in
    networks) cmd_networks ;;
    vms)      cmd_vms ;;
    up)       cmd_networks; cmd_vms ;;
    status)   cmd_status ;;
    destroy)  cmd_destroy ;;
    *) sed -n '2,10p' "${BASH_SOURCE[0]}"; exit 2 ;;
  esac
}
main "$@"
