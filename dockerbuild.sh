#!/usr/bin/env bash
#
# dockerbuild.sh —— Docker Tag 发布脚本（Linux / Bash 版）
# 与 script/dockerbuild.ps1 逻辑保持一致
#
# 用法: ./dockerbuild.sh [版本标签]
# 示例: ./dockerbuild.sh v0.0.1
#

set -euo pipefail

# ── 参数解析 ──────────────────────────────────────────────
VERSION="${1:-}"
HELP_MODE=0

for arg in "$@"; do
  case "$arg" in
    -h|--help) HELP_MODE=1 ;;
  esac
done

usage() {
  cat <<'EOF'
用法: ./dockerbuild.sh [版本标签]
示例: ./dockerbuild.sh v0.0.1

参数:
  <版本标签>  Git 标签版本 (留空则自动计算)
  -h, --help  显示帮助
EOF
}

if [[ "$HELP_MODE" -eq 1 ]]; then usage; exit 0; fi

# ── 彩色日志函数 ──────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}➤ $*${NC}"; }
log_success() { echo -e "${GREEN}✔ $*${NC}"; }
log_warn()    { echo -e "${YELLOW}⚠ $*${NC}"; }
log_error()   { echo -e "${RED}✖ $*${NC}" >&2; }

banner() {
  printf "${BLUE}%*s${NC}\n" 46 '' | tr ' ' '='
  echo -e "${BLUE}Docker Tag 发布脚本${NC}"
  echo -e "${BLUE}版本: $VERSION${NC}"
  printf "${BLUE}%*s${NC}\n" 46 '' | tr ' ' '='
}

# ── 前置检查 ──────────────────────────────────────────────
ensure_git() {
  if ! command -v git &>/dev/null; then
    log_error "未找到 git 命令，请先安装 Git 并确保在 PATH 中。"
    exit 1
  fi
}

ensure_clean_working_tree() {
  # 检查工作区是否干净；如存在改动则要求人工确认后继续打标签与推送
  local changes
  changes=$(git status --porcelain 2>/dev/null || true)
  if [[ -n "$changes" ]]; then
    log_warn "检测到未提交/已暂存/未跟踪的改动：\n$changes"
    read -rp "仍要继续打标签并推送吗？输入 YES 继续，其它任意输入中止： " answer
    if [[ "$(echo "$answer" | tr '[:lower:]' '[:upper:]')" != "YES" ]]; then
      log_error "已取消打标签与推送。"
      exit 1
    fi
    log_warn "已确认忽略当前改动，将继续打标签与推送。"
  fi
}

# ── 版本计算 ──────────────────────────────────────────────
get_latest_tag() {
  # 获取最新标签（按语义版本排序）
  local tags
  tags=$(git tag --list 'v*' --sort=-version:refname 2>/dev/null || true)
  if [[ -n "$tags" ]]; then
    echo "$tags" | head -n1 | tr -d ' \t'
  fi
}

bump_tail() {
  # 将尾数 +1：优先识别 vMAJOR.MINOR.PATCH，否则对末尾数字增量
  local tag="$1"
  if [[ -z "$tag" ]]; then echo "v0.0.1"; return; fi

  # 尝试语义版本匹配 vMAJOR.MINOR.PATCH
  if [[ "$tag" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    local major="${BASH_REMATCH[1]}"
    local minor="${BASH_REMATCH[2]}"
    local patch=$(( BASH_REMATCH[3] + 1 ))
    echo "v${major}.${minor}.${patch}"
    return
  fi

  # 兜底：对末尾数字增量
  if [[ "$tag" =~ ^(.*[^0-9])([0-9]+)$ ]]; then
    local prefix="${BASH_REMATCH[1]}"
    local tail=$(( BASH_REMATCH[2] + 1 ))
    echo "${prefix}${tail}"
    return
  fi

  echo "${tag}-1"
}

# ══════════════════════════════════════════════════════════
#                         主流程
# ══════════════════════════════════════════════════════════
ensure_git
ensure_clean_working_tree

# 若未显式传入版本参数，则依据最新标签自动计算
if [[ -z "$VERSION" ]]; then
  latest="$(get_latest_tag)"
  if [[ -n "$latest" ]]; then
    log_info "检测到当前最新标签: $latest"
    VERSION="$(bump_tail "$latest")"
    log_info "自动计算版本: $VERSION"
  else
    log_warn "未发现任何标签，使用默认 v0.0.1"
    VERSION="v0.0.1"
  fi
fi

banner

# 创建 Git 标签
log_info "创建 Git 标签 $VERSION"
if git rev-parse "$VERSION" &>/dev/null; then
  log_warn "标签 $VERSION 已存在，跳过创建"
else
  branch="$(git branch --show-current 2>/dev/null || echo 'unknown')"
  git tag "$VERSION"
  log_success "标签 $VERSION 创建成功（分支 ${branch})"
fi

# 推送标签到远程 origin
log_info "推送标签到远程 origin"
git push origin "$VERSION"
log_success "标签 $VERSION 推送完成"
