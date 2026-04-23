#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="pm3"
REPOSITORY="pypi" # pypi | testpypi
REBUILD=false

usage() {
  echo "Usage: ./upload.sh [--rebuild] [pypi|testpypi]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rebuild)
      REBUILD=true
      shift
      ;;
    pypi|testpypi)
      REPOSITORY="$1"
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Invalid argument: $1"
      usage
      ;;
  esac
done

if [[ "${REBUILD}" == "true" ]]; then
  echo "==> Rebuilding ${PROJECT_NAME} via build.sh"
  ./build.sh
fi

echo "==> Validating artifacts"
python -m twine check dist/*

shopt -s nullglob
artifacts=(dist/${PROJECT_NAME}-*.whl dist/${PROJECT_NAME}-*.tar.gz)
shopt -u nullglob

if [[ ${#artifacts[@]} -eq 0 ]]; then
  echo "No artifacts found for project '${PROJECT_NAME}' in dist/"
  exit 1
fi

echo "==> Upload target: ${REPOSITORY}"
echo "==> Artifacts:"
printf ' - %s\n' "${artifacts[@]}"

python -m twine upload --repository "${REPOSITORY}" --verbose "${artifacts[@]}"
