import { NextResponse } from "next/server";

const FLASK_API_URL = process.env.FLASK_API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const response = await fetch(`${FLASK_API_URL}/api/health`, {
      next: { revalidate: 0 },
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "unhealthy", message: `Backend returned ${response.status}` },
        { status: 503 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Health check error:", error);
    return NextResponse.json(
      { status: "unhealthy", message: "Unable to connect to backend server" },
      { status: 503 }
    );
  }
}
