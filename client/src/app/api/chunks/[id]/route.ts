import { NextRequest, NextResponse } from "next/server";

const FLASK_API_URL = process.env.FLASK_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    if (!id) {
      return NextResponse.json(
        { error: "Invalid request", message: "Chunk ID is required" },
        { status: 400 }
      );
    }

    const response = await fetch(`${FLASK_API_URL}/api/chunks/${id}`);

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: "Not found", message: "Chunk not found" },
          { status: 404 }
        );
      }
      return NextResponse.json(
        { error: "Backend error", message: `Backend returned ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Chunk fetch error:", error);
    return NextResponse.json(
      { error: "Internal error", message: "An unexpected error occurred" },
      { status: 500 }
    );
  }
}
