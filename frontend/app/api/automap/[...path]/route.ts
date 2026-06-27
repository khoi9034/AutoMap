import { NextRequest, NextResponse } from "next/server";

const DEFAULT_AUTOMAP_API_SERVER_URL = "https://automap-api.onrender.com";
const FORWARDED_REQUEST_HEADERS = new Set(["accept", "content-type"]);

type RouteContext = {
  params: Promise<{ path?: string[] }>;
};

function normalizeServerUrl(): URL {
  const raw = (process.env.AUTOMAP_API_SERVER_URL || DEFAULT_AUTOMAP_API_SERVER_URL).trim().replace(/\/+$/, "");
  const url = new URL(raw || DEFAULT_AUTOMAP_API_SERVER_URL);
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    throw new Error("AutoMap API server URL must use HTTP or HTTPS.");
  }
  return url;
}

function sanitizePath(path: string[] = []): string {
  for (const segment of path) {
    if (!segment || segment === "." || segment === ".." || segment.includes("\\") || segment.includes(":")) {
      throw new Error("Invalid AutoMap API proxy path.");
    }
  }
  return path.map((segment) => encodeURIComponent(segment)).join("/");
}

function buildBackendUrl(path: string[], requestUrl: string): URL {
  const serverUrl = normalizeServerUrl();
  const safePath = sanitizePath(path);
  const incoming = new URL(requestUrl);
  const target = new URL(`/api/${safePath}`, serverUrl);
  target.search = incoming.search;
  return target;
}

function forwardedHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  for (const [key, value] of request.headers.entries()) {
    const lowered = key.toLowerCase();
    if (FORWARDED_REQUEST_HEADERS.has(lowered)) {
      headers.set(key, value);
    }
  }
  return headers;
}

async function proxyAutomapRequest(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  let target: URL;
  try {
    const { path = [] } = await context.params;
    target = buildBackendUrl(path, request.url);
  } catch {
    return NextResponse.json({ error: "invalid_proxy_path", message: "Invalid AutoMap API proxy path." }, { status: 400 });
  }

  const controller = new AbortController();
  const timeoutMs = target.pathname === "/api/composer/generate" ? 240000 : 60000;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
    const response = await fetch(target, {
      method: request.method,
      headers: forwardedHeaders(request),
      body: body || undefined,
      cache: "no-store",
      signal: controller.signal,
    });
    const responseBody = await response.arrayBuffer();
    const headers = new Headers();
    const contentType = response.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
    return new NextResponse(responseBody, { status: response.status, headers });
  } catch (exc) {
    const backend = normalizeServerUrl();
    const errorCategory = exc instanceof Error && exc.name === "AbortError" ? "timeout" : "network";
    return NextResponse.json(
      {
        error: "backend_unreachable",
        error_category: errorCategory,
        backend_host: backend.host,
        path: target.pathname,
        message: "Vercel proxy could not reach Render backend.",
      },
      { status: 502 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

export function OPTIONS(): NextResponse {
  return new NextResponse(null, { status: 204 });
}

export async function GET(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  return proxyAutomapRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  return proxyAutomapRequest(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  return proxyAutomapRequest(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  return proxyAutomapRequest(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  return proxyAutomapRequest(request, context);
}
