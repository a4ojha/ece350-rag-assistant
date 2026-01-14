import { NextRequest, NextResponse } from "next/server";

const FLASK_API_URL = process.env.FLASK_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ lecture: string }> }
) {
  try {
    const { lecture } = await params;

    if (!lecture) {
      return NextResponse.json(
        { error: "Invalid request", message: "Lecture number is required" },
        { status: 400 }
      );
    }

    // Validate lecture number
    const lectureNum = parseInt(lecture, 10);
    if (isNaN(lectureNum) || lectureNum < 1 || lectureNum > 30) {
      return NextResponse.json(
        { error: "Invalid request", message: "Invalid lecture number" },
        { status: 400 }
      );
    }

    const response = await fetch(`${FLASK_API_URL}/api/pdfs/${lectureNum}`);

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: "Not found", message: "PDF not found" },
          { status: 404 }
        );
      }
      return NextResponse.json(
        { error: "Backend error", message: `Backend returned ${response.status}` },
        { status: response.status }
      );
    }

    // Stream the PDF response
    const pdfBuffer = await response.arrayBuffer();

    return new NextResponse(pdfBuffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `inline; filename="L${lectureNum.toString().padStart(2, "0")}.pdf"`,
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (error) {
    console.error("PDF fetch error:", error);
    return NextResponse.json(
      { error: "Internal error", message: "An unexpected error occurred" },
      { status: 500 }
    );
  }
}
