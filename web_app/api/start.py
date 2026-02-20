import uvicorn
import os

if __name__ == "__main__":
    print("🚀 Starting Social Insights Backend...")
    uvicorn.run(
        "index:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
