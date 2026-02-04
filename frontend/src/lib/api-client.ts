import { getToken, clearToken } from "./auth";
import type {
  Token,
  TOTPSetupResponse,
  UserResponse,
  UserCreate,
  SourceResponse,
  SourceCreate,
  SourceUpdate,
  ArticleResponse,
  ArticleListResponse,
  BriefingResponse,
  CollectionStatus,
  SourceCollectionStatus,
  SummarizeResponse,
  IngestResponse,
  IngestAllResponse,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_V1}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    const error = await response.json().catch(() => ({ detail: "Unauthorized" }));
    throw new ApiError(error.detail || "Unauthorized", 401);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(error.detail || `API error: ${response.status}`, response.status);
  }

  return response.json();
}

// === Auth ===
export async function login(
  email: string,
  password: string,
  totpCode?: string
): Promise<Token> {
  const pwd = totpCode ? `${password}:${totpCode}` : password;
  const body = new URLSearchParams({ username: email, password: pwd });
  return request<Token>("/auth/login", { method: "POST", body });
}

export async function register(data: UserCreate): Promise<UserResponse> {
  return request<UserResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function setup2FA(): Promise<TOTPSetupResponse> {
  return request<TOTPSetupResponse>("/auth/2fa/setup", { method: "POST" });
}

export async function verify2FA(code: string): Promise<{ message: string }> {
  return request<{ message: string }>("/auth/2fa/verify", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function disable2FA(code: string): Promise<{ message: string }> {
  return request<{ message: string }>("/auth/2fa", {
    method: "DELETE",
    body: JSON.stringify({ code }),
  });
}

// === Users ===
export async function getCurrentUser(): Promise<UserResponse> {
  return request<UserResponse>("/users/me");
}

// === Sources ===
export async function listSources(params?: {
  skip?: number;
  limit?: number;
  active_only?: boolean;
}): Promise<SourceResponse[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip !== undefined) searchParams.set("skip", String(params.skip));
  if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params?.active_only !== undefined)
    searchParams.set("active_only", String(params.active_only));
  const qs = searchParams.toString();
  return request<SourceResponse[]>(`/sources/${qs ? `?${qs}` : ""}`);
}

export async function getSource(id: string): Promise<SourceResponse> {
  return request<SourceResponse>(`/sources/${id}`);
}

export async function createSource(data: SourceCreate): Promise<SourceResponse> {
  return request<SourceResponse>("/sources/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSource(
  id: string,
  data: SourceUpdate
): Promise<SourceResponse> {
  return request<SourceResponse>(`/sources/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteSource(id: string): Promise<void> {
  return request<void>(`/sources/${id}`, { method: "DELETE" });
}

// === Articles ===
export async function listArticles(params?: {
  page?: number;
  per_page?: number;
  source_id?: string;
}): Promise<ArticleListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page !== undefined) searchParams.set("page", String(params.page));
  if (params?.per_page !== undefined)
    searchParams.set("per_page", String(params.per_page));
  if (params?.source_id) searchParams.set("source_id", params.source_id);
  const qs = searchParams.toString();
  return request<ArticleListResponse>(`/articles/${qs ? `?${qs}` : ""}`);
}

export async function getArticle(id: string): Promise<ArticleResponse> {
  return request<ArticleResponse>(`/articles/${id}`);
}

export async function deleteArticle(id: string): Promise<void> {
  return request<void>(`/articles/${id}`, { method: "DELETE" });
}

export async function summarizeArticle(id: string): Promise<SummarizeResponse> {
  return request<SummarizeResponse>(`/articles/${id}/summarize`, {
    method: "POST",
  });
}

export async function ingestArticle(id: string): Promise<IngestResponse> {
  return request<IngestResponse>(`/articles/${id}/ingest`, { method: "POST" });
}

export async function ingestAllArticles(): Promise<IngestAllResponse> {
  return request<IngestAllResponse>("/articles/ingest-all", { method: "POST" });
}

// === Collection ===
export async function collectAll(): Promise<{ message: string; status: string }> {
  return request<{ message: string; status: string }>("/collection/collect-all", {
    method: "POST",
  });
}

export async function getCollectionStatus(): Promise<CollectionStatus> {
  return request<CollectionStatus>("/collection/status");
}

export async function collectSource(id: string): Promise<{ message: string; status: string }> {
  return request<{ message: string; status: string }>(`/collection/collect/${id}`, {
    method: "POST",
  });
}

export async function getSourceCollectionStatus(id: string): Promise<SourceCollectionStatus> {
  return request<SourceCollectionStatus>(`/collection/status/${id}`);
}

// === Intelligence ===
export async function createBriefing(query: string): Promise<BriefingResponse> {
  return request<BriefingResponse>("/intelligence/briefing", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export { ApiError };
