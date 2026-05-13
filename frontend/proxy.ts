import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const token = process.env.LIST_TOKEN;
  if (!token) return NextResponse.next();

  const provided = new URL(request.url).searchParams.get("token");
  if (provided === token) return NextResponse.next();

  return new NextResponse("Unauthorized", { status: 401 });
}

export const config = {
  matcher: "/",
};
