#!/bin/bash
# ─────────────────────────────────────────
# CarpoolSafe — One Command Startup
# Usage: bash start.sh
# ─────────────────────────────────────────
set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo ""
echo -e "${CYAN}  ╔═══════════════════════════════════════╗${NC}"
echo -e "${CYAN}  ║  🚗  CarpoolSafe — Full Stack App      ║${NC}"
echo -e "${CYAN}  ╚═══════════════════════════════════════╝${NC}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python 3 not found. Install from https://python.org${NC}"; exit 1
fi
echo -e "${GREEN}✓ Python: $(python3 --version)${NC}"

# Check PostgreSQL
if ! command -v psql &>/dev/null; then
    echo -e "${YELLOW}⚠ PostgreSQL not found. Make sure DATABASE_URL in .env is correct.${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL available${NC}"
fi

# Load env
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
    echo -e "${GREEN}✓ Loaded .env${NC}"
fi

echo ""
echo -e "${YELLOW}[1/3] Installing backend dependencies...${NC}"
pip install -r backend/requirements.txt -q --disable-pip-version-check
echo -e "${GREEN}✓ Backend deps ready${NC}"

echo -e "${YELLOW}[2/3] Installing frontend dependencies...${NC}"
pip install -r frontend/requirements.txt -q --disable-pip-version-check
echo -e "${GREEN}✓ Frontend deps ready${NC}"

echo ""
echo -e "${YELLOW}[3/3] Starting backend on http://localhost:8000 ...${NC}"
python3 run_backend.py &
BACKEND_PID=$!
sleep 4

if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Backend running (PID: $BACKEND_PID)${NC}"
    echo -e "${GREEN}  → API Docs: http://localhost:8000/docs${NC}"
else
    echo -e "${RED}✗ Backend failed to start. Check your DATABASE_URL in .env${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Starting frontend on http://localhost:8501 ...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd frontend
BACKEND_URL=http://localhost:8000 \
GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY} \
streamlit run app.py

# Cleanup
kill $BACKEND_PID 2>/dev/null
