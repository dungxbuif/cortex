#!/bin/sh
export GOCACHE="$(pwd)/.gocache"
export GOPATH="$(pwd)/.gopath"
export FINANCE_TEST_DATABASE_URL="postgres://dev:password@localhost:5432/cortex?sslmode=disable"
mkdir -p "$GOCACHE" "$GOPATH"
go test -v ./internal/modules/finance/service/tests/...
