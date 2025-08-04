# 🚀 Quick Start - Local Development

## For KMP Android App Testing

### 1. Start the Backend Server

```bash
# Make sure you're in the backend directory
cd /Users/micky/PycharmProjects/PratikoAi-BE

# Install dependencies (if not already done)
uv sync

# Start the development server
make dev
```

The server will be available at: **http://localhost:8000**

### 2. Test Backend Connection

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test chatbot endpoint
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, test message"}'
```

### 3. Configure Android App

In your KMP Android app, set the base URL to:
```
http://10.0.2.2:8000  # For Android Emulator
# or
http://192.168.1.XXX:8000  # For physical device (your local IP)
```

### 4. Available Endpoints for KMP

- **Chat**: `POST /api/v1/chatbot/chat`
- **Health**: `GET /api/v1/health` 
- **Auth Register**: `POST /api/v1/auth/register`
- **Auth Login**: `POST /api/v1/auth/login`

### 5. Check Server Logs

The development server will show real-time logs of API calls from your Android app.

### 6. Quick Debug Commands

```bash
# Check if server is running
lsof -i :8000

# View recent logs
tail -f logs/app.log

# Check environment
echo $ENVIRONMENT
```

Ready to test! 📱