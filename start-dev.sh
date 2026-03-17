#!/bin/bash

# 🥬 Veg Vibe - Development Server Startup Script

set -e

echo "🥬 Veg Vibe - Starting Development Servers..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Start Backend
echo -e "${BLUE}Starting Backend API...${NC}"
cd backend
source venv/bin/activate || . venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend running on http://localhost:8000${NC}"
echo -e "   📖 API Docs: http://localhost:8000/docs"
echo ""

cd ..

# Start Frontend
echo -e "${BLUE}Starting Frontend Development Server...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✅ Frontend running on http://localhost:5173${NC}"
echo ""

echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
