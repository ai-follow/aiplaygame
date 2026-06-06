.DEFAULT_GOAL := help

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
NPM ?= npm
FRONTEND_DIR := frontend
PYTHONPATH := src
BOTZONE_ZIP := dist/botzone-agent.zip
PLAYERS ?= douzero,douzero,douzero
MATCHES ?= 1000
PORT ?= 5173

.PHONY: help install install-python install-frontend dev dev-api dev-web test test-py lint lint-py lint-web build build-web local eval package-botzone smoke-botzone clean

help:
	@echo "AI 斗地主常用命令"
	@echo ""
	@echo "安装:"
	@echo "  make install           安装 Python dev 依赖和前端依赖"
	@echo "  make install-python    安装 Python 包: pip install -e .[dev]"
	@echo "  make install-frontend  安装前端依赖"
	@echo ""
	@echo "开发:"
	@echo "  make dev               同时启动后端 API 和前端 Vite"
	@echo "  make dev-api           启动后端 API，默认 127.0.0.1:8000"
	@echo "  make dev-web           启动前端，默认 PORT=5173"
	@echo ""
	@echo "校验:"
	@echo "  make test              运行 Python 测试"
	@echo "  make lint              运行 Python + 前端 lint"
	@echo "  make build             运行前端生产构建"
	@echo ""
	@echo "运行:"
	@echo "  make local             终端跑一局本地比赛，PLAYERS=$(PLAYERS)"
	@echo "  make eval              自对弈评估，MATCHES=$(MATCHES)"
	@echo "  make package-botzone   打包 Botzone zip 到 $(BOTZONE_ZIP)"
	@echo "  make smoke-botzone     用 fixture smoke-run Botzone zip"
	@echo "  make clean             删除常见缓存和构建产物"

install: install-python install-frontend

install-python:
	$(PIP) install -e ".[dev]"

install-frontend:
	$(NPM) install --prefix $(FRONTEND_DIR)

dev:
	$(MAKE) -j2 dev-api dev-web

dev-api:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aiplaygame.cli.server

dev-web:
	$(NPM) run dev --prefix $(FRONTEND_DIR) -- --port $(PORT)

test: test-py

test-py:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest

lint: lint-py lint-web

lint-py:
	$(PYTHON) -m ruff check .

lint-web:
	$(NPM) run lint --prefix $(FRONTEND_DIR)

build: build-web

build-web:
	$(NPM) run build --prefix $(FRONTEND_DIR)

local:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aiplaygame.cli.runner local --players $(PLAYERS)

eval:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aiplaygame.cli.eval self-play --players $(PLAYERS) --matches $(MATCHES)

package-botzone:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aiplaygame.cli.agent package --out $(BOTZONE_ZIP)

smoke-botzone: package-botzone
	$(PYTHON) $(BOTZONE_ZIP) < tests/fixtures/botzone_turn.json

clean:
	rm -rf .pytest_cache .ruff_cache frontend/dist frontend/.vite dist/botzone-agent.zip
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
