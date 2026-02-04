// API response types matching FastAPI backend schemas

// === Auth ===
export interface Token {
  access_token: string;
  token_type: string;
}

export interface TOTPSetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_code_base64: string | null;
}

// === User ===
export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name?: string;
}

// === Source ===
export type SourceType = "rss" | "newsapi" | "static";

export interface SourceResponse {
  id: string;
  name: string;
  url: string | null;
  description: string | null;
  is_active: boolean;
  source_type: SourceType;
  source_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SourceCreate {
  name: string;
  url?: string;
  description?: string;
  is_active?: boolean;
  source_type?: SourceType;
  source_config?: Record<string, unknown>;
}

export interface SourceUpdate {
  name?: string;
  url?: string;
  description?: string;
  is_active?: boolean;
  source_type?: SourceType;
  source_config?: Record<string, unknown>;
}

// === Article ===
export interface ArticleResponse {
  id: string;
  source_id: string;
  title: string;
  url: string;
  content: string | null;
  summary: string | null;
  author: string | null;
  published_at: string | null;
  fetched_at: string;
  created_at: string;
  updated_at: string;
}

export interface ArticleListResponse {
  items: ArticleResponse[];
  total: number;
  page: number;
  per_page: number;
}

// === Intelligence ===
export interface BriefingResponse {
  query: string;
  briefing: string;
}

// === Collection ===
export interface CollectionStatus {
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  result: CollectAllResult | null;
  error: string | null;
}

export interface CollectAllResult {
  sources_processed: number;
  total_fetched: number;
  total_new: number;
  total_skipped: number;
  total_ingested: number;
  per_source: Record<string, unknown>;
}

export interface CollectSourceResult {
  source: string;
  fetched: number;
  new: number;
  skipped: number;
  ingested: number;
}

export interface SourceCollectionStatus {
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  result: CollectSourceResult | null;
  error: string | null;
}

// === Summarize / Ingest ===
export interface SummarizeResponse {
  article_id: string;
  summary: string;
}

export interface IngestResponse {
  article_id: string;
  status: string;
  chunks_created: number;
}

export interface IngestAllResponse {
  status: string;
  articles_ingested: number;
  articles_failed: number;
  total_chunks_created: number;
}
