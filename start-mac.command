#!/bin/bash
set -e
cd "$(dirname "$0")"

# Prefer a modern, explicitly versioned Python. macOS often provides python3=3.9.
supported_python() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

PYTHON=""
if [ -n "${KOREN_PYTHON:-}" ]; then
  if supported_python "$KOREN_PYTHON"; then
    PYTHON="$KOREN_PYTHON"
  else
    echo "KOREN_PYTHON не сочи към работещ Python 3.11 или по-нов: $KOREN_PYTHON"
    exit 1
  fi
else
  for candidate in python3.12 python3.13 python3.11 python3.14 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && supported_python "$candidate"; then
      PYTHON="$(command -v "$candidate")"
      break
    fi
  done

  # Versioned Homebrew Python can be installed but absent from the shell PATH.
  if [ -z "$PYTHON" ] && command -v brew >/dev/null 2>&1; then
    for version in 3.12 3.13 3.11 3.14; do
      prefix="$(brew --prefix "python@$version" 2>/dev/null || true)"
      if [ -n "$prefix" ] && supported_python "$prefix/bin/python$version"; then
        PYTHON="$prefix/bin/python$version"
        break
      fi
    done
  fi
fi

if [ -z "$PYTHON" ]; then
  echo "Нужен е Python 3.11 или по-нов."
  echo "На Mac с Homebrew изпълни: brew install python@3.12"
  echo "После стартирай отново: ./start-mac.command"
  exit 1
fi

echo "Използвам: $($PYTHON --version) ($PYTHON)"

# Retain any existing environment as a backup if it is broken or uses an old Python.
VENV_PY="$PWD/.venv/bin/python"
if [ -d .venv ] && { [ ! -x "$VENV_PY" ] || ! supported_python "$VENV_PY"; }; then
  backup=".venv.backup-$(date +%Y%m%d-%H%M%S)"
  n=1
  while [ -e "$backup" ]; do
    backup=".venv.backup-$(date +%Y%m%d-%H%M%S)-$n"
    n=$((n + 1))
  done
  echo "Запазвам старата виртуална среда като $backup"
  mv .venv "$backup"
fi

if [ ! -d .venv ]; then
  echo "Създавам виртуална среда..."
  "$PYTHON" -m venv .venv
fi

VENV_PY="$PWD/.venv/bin/python"
echo "Инсталирам необходимите зависимости..."
"$VENV_PY" -m pip install -r requirements.txt

if [ -z "${ADMIN_PASSWORD:-}" ]; then
  echo "Задай парола за администратора (няма да се показва):"
  read -r -s -p "Парола: " ADMIN_PASSWORD
  echo
fi
if [ "${#ADMIN_PASSWORD}" -lt 12 ]; then
  echo "Паролата трябва да има поне 12 символа."
  exit 1
fi

export ADMIN_PASSWORD
export APP_BASE_URL="${APP_BASE_URL:-http://127.0.0.1:8080}"
echo "МАГАЗИН: http://127.0.0.1:8080"
echo "АДМИН:  http://127.0.0.1:8080/admin"
exec "$VENV_PY" -m uvicorn server:app --host 127.0.0.1 --port 8080
