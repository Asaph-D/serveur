#!/usr/bin/env bash
# Publie bootstrap.json sur GitHub Pages (dépôt Portfolio) via l'API GitHub.
# Permet d'avoir api_remote à jour sans domaine propre (tunnel trycloudflare).
#
# Prérequis : token PAT dans /etc/provision/github-token (scope repo)
# Usage : bash scripts/publish-bootstrap-github.sh [--force]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GCFG="$ROOT/network/global-config.env"
BOOTSTRAP="$ROOT/network/github-pages/provision/bootstrap.json"

# shellcheck disable=SC1091
source "$GCFG"

if [[ "${GITHUB_BOOTSTRAP_PUBLISH:-no}" != "yes" ]]; then
	exit 0
fi

[[ -f "$BOOTSTRAP" ]] || { echo "bootstrap.json introuvable : $BOOTSTRAP" >&2; exit 1; }

GITHUB_TOKEN=""
TOKEN_FILE="${GITHUB_TOKEN_FILE:-/etc/provision/github-token}"
if [[ -r "$TOKEN_FILE" ]]; then
	GITHUB_TOKEN="$(tr -d '[:space:]' <"$TOKEN_FILE")"
elif [[ -f "$TOKEN_FILE" ]] && command -v sudo >/dev/null 2>&1; then
	GITHUB_TOKEN="$(sudo cat "$TOKEN_FILE" 2>/dev/null | tr -d '[:space:]' || true)"
fi
if [[ -z "$GITHUB_TOKEN" && -r /etc/provision/provision-secrets.env ]]; then
	# shellcheck disable=SC1091
	source /etc/provision/provision-secrets.env
	GITHUB_TOKEN="${GITHUB_TOKEN:-}"
fi
if [[ -z "$GITHUB_TOKEN" ]]; then
	echo "Token GitHub absent ou illisible — créez /etc/provision/github-token (PAT scope repo)" >&2
	exit 1
fi

API_REMOTE="$(python3 -c "import json; print(json.load(open('$BOOTSTRAP')).get('api_remote',''))" 2>/dev/null || true)"
PBX_IP="$(python3 -c "import json; print(json.load(open('$BOOTSTRAP')).get('pbx_lan_ip',''))" 2>/dev/null || true)"
if [[ -z "$API_REMOTE" ]]; then
	echo "api_remote vide dans bootstrap — sync-global-config d'abord" >&2
	exit 1
fi

ENCODED="$(base64 -w0 <"$BOOTSTRAP")"
LOCAL_HASH="$(sha256sum "$BOOTSTRAP" | awk '{print $1}')"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

CURL_GH=(curl -fsS --connect-timeout 5 --max-time 20)

github_put_bootstrap() {
	local repo="$1"
	local branch="$2"
	local remote_path="$3"
	local label="$4"

	local sha="" remote_hash=""
	local api_get="https://api.github.com/repos/${repo}/contents/${remote_path}?ref=${branch}"
	local existing
	existing="$("${CURL_GH[@]}" -H "Authorization: Bearer ${GITHUB_TOKEN}" \
		-H "Accept: application/vnd.github+json" "$api_get" 2>/dev/null || true)"

	if [[ -n "$existing" ]]; then
		sha="$(echo "$existing" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || true)"
		remote_hash="$(echo "$existing" | python3 -c "
import json,sys,base64,hashlib
d=json.load(sys.stdin)
raw=base64.b64decode(d.get('content',''))
print(hashlib.sha256(raw).hexdigest())
" 2>/dev/null || true)"
		if [[ "$FORCE" -eq 0 && -n "$remote_hash" && "$remote_hash" == "$LOCAL_HASH" ]]; then
			echo "${label} : déjà à jour (hash identique)."
			return 0
		fi
	fi

	local msg="chore(provision): bootstrap pbx_lan_ip=${PBX_IP} api_remote=${API_REMOTE}"
	local payload
	payload="$(python3 -c "
import json, sys
print(json.dumps({
    'message': sys.argv[1],
    'content': sys.argv[2],
    'branch': sys.argv[3],
    **({'sha': sys.argv[4]} if sys.argv[4] else {}),
}))
" "$msg" "$ENCODED" "$branch" "$sha")"

	local http
	http="$("${CURL_GH[@]}" -o /tmp/bootstrap-publish.json -w '%{http_code}' \
		-X PUT \
		-H "Authorization: Bearer ${GITHUB_TOKEN}" \
		-H "Accept: application/vnd.github+json" \
		"https://api.github.com/repos/${repo}/contents/${remote_path}" \
		-d "$payload")"

	if [[ "$http" != "200" && "$http" != "201" ]]; then
		echo "Échec ${label} (HTTP ${http}) :" >&2
		cat /tmp/bootstrap-publish.json >&2
		return 1
	fi
	echo "${label} : publié → https://github.com/${repo}/blob/${branch}/${remote_path}"
}

BRANCH="${GITHUB_BOOTSTRAP_BRANCH:-main}"
github_put_bootstrap \
	"${GITHUB_BOOTSTRAP_REPO:-asaph-d/Portfolio}" \
	"$BRANCH" \
	"${GITHUB_BOOTSTRAP_PATH:-provision/bootstrap.json}" \
	"Portfolio (GitHub Pages)"

if [[ -n "${GITHUB_BOOTSTRAP_MIRROR_REPO:-}" ]]; then
	github_put_bootstrap \
		"${GITHUB_BOOTSTRAP_MIRROR_REPO}" \
		"$BRANCH" \
		"${GITHUB_BOOTSTRAP_MIRROR_PATH:-network/github-pages/provision/bootstrap.json}" \
		"Miroir serveur"
fi

echo "Discovery : ${PROVISION_DISCOVERY_URL}"
echo "  pbx_lan_ip : ${PBX_IP}"
echo "  api_remote : ${API_REMOTE}"
