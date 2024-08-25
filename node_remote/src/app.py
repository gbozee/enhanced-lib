import os
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from enhanced_lib.exchange.phoenixd_handler import PhoenixdHandler

API_KEY = os.getenv("NODE_API_KEY")
NODE_URL = os.getenv("NODE_BASE_URL")

wallet = PhoenixdHandler(base_url=NODE_URL, api_key=API_KEY)


async def homepage(request):
    return JSONResponse({"message": "Welcome to the Node Remote API"})


async def health_check(request):
    return JSONResponse({"status": "healthy"})


routes = [
    Route("/", endpoint=homepage),
    Route("/health", endpoint=health_check),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
