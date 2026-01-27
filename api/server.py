
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, health
from api.dependencies import PipelineFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown events.
    Crucial for closing async connections gracefully.
    """
    # Startup: Ensure pipeline is ready (optional)
    await PipelineFactory.get_instance()
    yield
    # later add cleanup logic here
    # e.g., await PipelineFactory.get_instance().retriever.close()
    print("Shutting down RAG API...")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Production RAG API",
        version="1.0.0",
        lifespan=lifespan
    )

    # Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Change this in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routes
    app.include_router(health.router, tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])

    return app

app = create_app()