"""
Flask REST API for ECE 350 RAG Assistant.
Wraps the existing RAG pipeline for frontend consumption.
"""

import os
from dotenv import load_dotenv

from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import time
from pathlib import Path

from rag_pipeline import ECE350RAG
from data_models import Chunk

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# =============================================================================
# Rate Limiting Configuration
# =============================================================================
# Only enabled in production (to set RATE_LIMIT_ENABLED=true in deployment environment)
# Local development has unlimited queries by default
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
DAILY_QUERY_LIMIT = int(os.getenv("DAILY_QUERY_LIMIT", "5"))

# Initialize limiter (uses in-memory storage by default)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    enabled=RATE_LIMIT_ENABLED,
    default_limits=[],  # No default limits - we apply them selectively
    storage_uri="memory://",
)

@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Custom handler for rate limit errors."""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": f"Daily query limit ({DAILY_QUERY_LIMIT}) reached. This demo is limited to manage API costs. Try again tomorrow, or clone the repo to run locally with your own API key.",
        "limit": DAILY_QUERY_LIMIT,
        "reset": "midnight UTC"
    }), 429

# Global RAG instance (initialized on startup)
rag: ECE350RAG = None

# Configuration
LECTURE_PDF_DIR = Path("compiled")
CHUNKS_FILE = "lecture_chunks.json"
EMBEDDINGS_FILE = "embeddings.npy"


def require_rag(f):
    """Decorator to ensure RAG system is initialized."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if rag is None:
            return jsonify({
                "error": "RAG system not initialized",
                "message": "Server is still starting up. Please try again."
            }), 503
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# Health & Metadata Endpoints
# =============================================================================

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy" if rag else "initializing",
        "rag_ready": rag is not None,
        "chunks_loaded": len(rag.chunks) if rag else 0,
        "index_ready": rag.index is not None if rag else False
    })


@app.route("/api/info", methods=["GET"])
@require_rag
def system_info():
    """Return system metadata."""
    # Count lectures
    lecture_nums = set(c.hierarchy.lecture_num for c in rag.chunks)

    return jsonify({
        "total_chunks": len(rag.chunks),
        "lectures_indexed": sorted(list(lecture_nums)),
        "num_lectures": len(lecture_nums),
        "embedding_model": rag.embedding_model,
        "llm_model": rag.llm_model,
        "index_size": rag.index.ntotal if rag.index else 0
    })


# =============================================================================
# Core Query Endpoint
# =============================================================================

@app.route("/api/query", methods=["POST"])
@limiter.limit(f"{DAILY_QUERY_LIMIT}/day")
@require_rag
def query():
    """
    Main query endpoint.

    Request body:
        {
            "question": "What is a context switch?",
            "top_k": 5  // optional, default 5
        }

    Response:
        RetrievalResult.to_dict() format with answer, sources, and metadata
    """
    data = request.get_json()

    if not data or "question" not in data:
        return jsonify({
            "error": "Missing required field",
            "message": "Request body must include 'question' field"
        }), 400

    question = data["question"].strip()
    if not question:
        return jsonify({
            "error": "Invalid question",
            "message": "Question cannot be empty"
        }), 400

    top_k = data.get("top_k", 5)
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        top_k = 5

    try:
        result = rag.ask(question, top_k=top_k, verbose=False)
        return jsonify(result.to_dict())
    except Exception as e:
        return jsonify({
            "error": "Query failed",
            "message": str(e)
        }), 500


# =============================================================================
# Chunk Endpoints
# =============================================================================

@app.route("/api/chunks/<chunk_id>", methods=["GET"])
@require_rag
def get_chunk(chunk_id: str):
    """
    Retrieve a specific chunk by ID.

    Response:
        Chunk.to_frontend_response() format
    """
    chunk = rag.get_chunk_by_id(chunk_id)

    if not chunk:
        return jsonify({
            "error": "Chunk not found",
            "message": f"No chunk with ID '{chunk_id}'"
        }), 404

    return jsonify(chunk.to_frontend_response())


@app.route("/api/chunks/<chunk_id>/context", methods=["GET"])
@require_rag
def get_chunk_context(chunk_id: str):
    """
    Get surrounding chunks for expanded context view.

    Query params:
        size: Number of chunks before/after (default 2, max 5)

    Response:
        {
            "central_chunk_id": "...",
            "chunks": [Chunk.to_frontend_response(), ...]
        }
    """
    size = request.args.get("size", 2, type=int)
    size = min(max(size, 1), 5)  # Clamp between 1 and 5

    surrounding = rag.get_surrounding_chunks(chunk_id, context_size=size)

    if not surrounding:
        return jsonify({
            "error": "Chunk not found",
            "message": f"No chunk with ID '{chunk_id}'"
        }), 404

    return jsonify({
        "central_chunk_id": chunk_id,
        "context_size": size,
        "chunks": [c.to_frontend_response() for c in surrounding]
    })


@app.route("/api/chunks/lecture/<int:lecture_num>", methods=["GET"])
@require_rag
def get_lecture_chunks(lecture_num: int):
    """
    Get all chunks for a specific lecture.

    Query params:
        preview_only: If true, return minimal data (default false)

    Response:
        {
            "lecture_num": 5,
            "lecture_title": "...",
            "total_chunks": 42,
            "chunks": [...]
        }
    """
    preview_only = request.args.get("preview_only", "false").lower() == "true"

    lecture_chunks = [c for c in rag.chunks if c.hierarchy.lecture_num == lecture_num]

    if not lecture_chunks:
        return jsonify({
            "error": "Lecture not found",
            "message": f"No chunks for lecture {lecture_num}"
        }), 404

    lecture_chunks.sort(key=lambda c: c.chunk_position_in_lecture)
    lecture_title = lecture_chunks[0].hierarchy.lecture_title

    if preview_only:
        chunks_data = [{
            "chunk_id": c.chunk_id,
            "section": c.hierarchy.section_title,
            "subsection": c.hierarchy.subsection_title,
            "position": c.chunk_position_in_lecture,
            "word_count": c.word_count
        } for c in lecture_chunks]
    else:
        chunks_data = [c.to_frontend_response() for c in lecture_chunks]

    return jsonify({
        "lecture_num": lecture_num,
        "lecture_title": lecture_title,
        "total_chunks": len(lecture_chunks),
        "chunks": chunks_data
    })


# =============================================================================
# PDF Serving Endpoints
# =============================================================================

@app.route("/api/pdfs/<int:lecture_num>", methods=["GET"])
def serve_pdf(lecture_num: int):
    """
    Serve lecture PDF file.

    Supports range requests for efficient PDF.js loading.
    """
    # Try common naming patterns
    patterns = [
        f"L{lecture_num:02d}.pdf",
        f"L{lecture_num}.pdf",
        f"lecture{lecture_num}.pdf",
        f"Lecture{lecture_num}.pdf"
    ]

    pdf_path = None
    for pattern in patterns:
        candidate = LECTURE_PDF_DIR / pattern
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        return jsonify({
            "error": "PDF not found",
            "message": f"No PDF found for lecture {lecture_num}",
            "searched_patterns": patterns
        }), 404

    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=pdf_path.name
    )


@app.route("/api/pdfs", methods=["GET"])
def list_pdfs():
    """List all available lecture PDFs."""
    if not LECTURE_PDF_DIR.exists():
        return jsonify({
            "available": [],
            "directory": str(LECTURE_PDF_DIR),
            "exists": False
        })

    pdfs = list(LECTURE_PDF_DIR.glob("*.pdf"))

    # Extract lecture numbers from filenames
    available = []
    for pdf in pdfs:
        name = pdf.stem  # e.g., "L05" or "lecture5"
        # Try to extract number
        import re
        match = re.search(r'(\d+)', name)
        if match:
            available.append({
                "lecture_num": int(match.group(1)),
                "filename": pdf.name,
                "url": f"/api/pdfs/{int(match.group(1))}"
            })

    available.sort(key=lambda x: x["lecture_num"])

    return jsonify({
        "available": available,
        "count": len(available)
    })


# =============================================================================
# Search Endpoints (for advanced features)
# =============================================================================

@app.route("/api/search/lectures", methods=["GET"])
@require_rag
def search_lectures():
    """
    Get lecture index with section breakdown.
    Useful for navigation/browsing UI.
    """
    lectures = {}

    for chunk in rag.chunks:
        lnum = chunk.hierarchy.lecture_num
        if lnum not in lectures:
            lectures[lnum] = {
                "lecture_num": lnum,
                "lecture_title": chunk.hierarchy.lecture_title,
                "sections": {},
                "total_chunks": 0
            }

        lectures[lnum]["total_chunks"] += 1

        section_id = chunk.hierarchy.section_id
        if section_id not in lectures[lnum]["sections"]:
            lectures[lnum]["sections"][section_id] = {
                "section_id": section_id,
                "section_title": chunk.hierarchy.section_title,
                "subsections": set(),
                "chunk_count": 0
            }

        lectures[lnum]["sections"][section_id]["chunk_count"] += 1
        if chunk.hierarchy.subsection_title:
            lectures[lnum]["sections"][section_id]["subsections"].add(
                chunk.hierarchy.subsection_title
            )

    # Convert sets to lists and format
    result = []
    for lnum in sorted(lectures.keys()):
        lecture = lectures[lnum]
        lecture["sections"] = [
            {
                **section,
                "subsections": sorted(list(section["subsections"]))
            }
            for section in lecture["sections"].values()
        ]
        result.append(lecture)

    return jsonify({
        "lectures": result,
        "total_lectures": len(result)
    })


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not found",
        "message": "The requested resource does not exist"
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": str(e)
    }), 500


# =============================================================================
# Initialization
# =============================================================================

def initialize_rag():
    """Initialize the RAG system."""
    global rag

    print("=" * 60)
    print("ECE 350 RAG API - Initializing...")
    print("=" * 60)

    # Check for required files
    if not os.path.exists(CHUNKS_FILE):
        print(f"ERROR: {CHUNKS_FILE} not found!")
        print("Run 'python latex_parser.py' first to generate chunks.")
        return False

    # Initialize RAG
    rag = ECE350RAG(
        chunks_file=CHUNKS_FILE,
        embedding_model="text-embedding-3-small",
        llm_model="gpt-4o-mini"
    )

    # Load or create embeddings
    if os.path.exists(EMBEDDINGS_FILE):
        rag.load_embeddings(EMBEDDINGS_FILE)
    else:
        print(f"\n{EMBEDDINGS_FILE} not found. Generating embeddings...")
        rag.create_embeddings(EMBEDDINGS_FILE)

    # Build index
    rag.build_faiss_index()

    print("\n" + "=" * 60)
    print("RAG API Ready!")
    print(f"  - {len(rag.chunks)} chunks loaded")
    print(f"  - FAISS index: {rag.index.ntotal} vectors")
    if RATE_LIMIT_ENABLED:
        print(f"  - Rate limiting: {DAILY_QUERY_LIMIT} queries/day per IP")
    else:
        print("  - Rate limiting: DISABLED (local development)")
    print("=" * 60 + "\n")

    return True


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ECE 350 RAG API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if initialize_rag():
        print(f"\nStarting server at http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop\n")
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    else:
        print("\nFailed to initialize RAG system. Exiting.")
        exit(1)
