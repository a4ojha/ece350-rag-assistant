import { NextRequest, NextResponse } from "next/server";

const FLASK_API_URL = process.env.FLASK_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate request body
    if (!body.question || typeof body.question !== "string") {
      return NextResponse.json(
        { error: "Invalid request", message: "Question is required" },
        { status: 400 }
      );
    }

    // Sanitize and validate input
    const question = body.question.trim();
    if (question.length === 0) {
      return NextResponse.json(
        { error: "Invalid request", message: "Question cannot be empty" },
        { status: 400 }
      );
    }

    if (question.length > 2000) {
      return NextResponse.json(
        { error: "Invalid request", message: "Question is too long (max 2000 characters)" },
        { status: 400 }
      );
    }

    const top_k = typeof body.top_k === "number" ? Math.min(Math.max(1, body.top_k), 10) : 5;

    // Forward to Flask API
    const response = await fetch(`${FLASK_API_URL}/api/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question, top_k }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        {
          error: "Backend error",
          message: errorData.message || `Backend returned ${response.status}`,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Query API error:", error);

    if (error instanceof Error && error.message.includes("fetch")) {
      return NextResponse.json(
        { error: "Connection error", message: "Unable to connect to backend server" },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: "Internal error", message: "An unexpected error occurred" },
      { status: 500 }
    );
  }
}
