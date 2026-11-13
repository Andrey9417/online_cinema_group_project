#!/bin/sh
set -e

echo "Configuring MinIO client..."
mc alias set minio http://"$MINIO_HOST":"$MINIO_PORT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

echo "Creating bucket '$MINIO_STORAGE' if missing..."
mc mb --ignore-existing minio/"$MINIO_STORAGE"

echo "Setting bucket policy to public read..."
mc anonymous set download minio/"$MINIO_STORAGE"
mc anonymous get minio/"$MINIO_STORAGE"

echo "MinIO configuration completed!"