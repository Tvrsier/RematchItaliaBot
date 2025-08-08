#!/usr/bin/env bash

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <version>"
  echo "Example: $0 1.0.0"
  exit 1
fi

VERSION=$1
BUILD_DIR="build/$VERSION"
BASE_NAME="rematch_bot"

echo "Building $BASE_NAME version $VERSION..."

mkdir -p "$BUILD_DIR"


STAGING_DIR="$BUILD_DIR/staging"
mkdir -p "$STAGING_DIR"

cp -r app "$STAGING_DIR"
cp launcher.py "$STAGING_DIR"
cp info.py "$STAGING_DIR"

pex -D "$STAGING_DIR" -r requirements.txt -m launcher -o "$BUILD_DIR/$BASE_NAME-$VERSION.pex"
cp .env.prod "$BUILD_DIR/.env"
cp -r data "$BUILD_DIR/" 2>/dev/null || true

rm -rf "$STAGING_DIR"

echo "Build completed: $BUILD_DIR/$BASE_NAME-$VERSION.pex"