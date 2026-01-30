"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import * as api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  Sparkles,
  Upload,
  Trash2,
} from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import type { ArticleResponse } from "@/types/api";

export default function ArticleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [article, setArticle] = useState<ArticleResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const fetchArticle = async () => {
      try {
        const data = await api.getArticle(id);
        setArticle(data);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Failed to load article");
      } finally {
        setIsLoading(false);
      }
    };
    fetchArticle();
  }, [id]);

  const handleSummarize = async () => {
    setIsSummarizing(true);
    try {
      const result = await api.summarizeArticle(id);
      setArticle((prev) => (prev ? { ...prev, summary: result.summary } : null));
      toast.success("Summary generated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Summarization failed");
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleIngest = async () => {
    setIsIngesting(true);
    try {
      const result = await api.ingestArticle(id);
      toast.success(`Ingested: ${result.chunks_created} chunks created`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ingestion failed");
    } finally {
      setIsIngesting(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteArticle(id);
      toast.success("Article deleted");
      router.push("/articles");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!article) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Article not found</p>
        <Button variant="link" onClick={() => router.push("/articles")}>
          Back to articles
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <Button variant="ghost" size="sm" onClick={() => router.push("/articles")}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to articles
      </Button>

      <div>
        <h1 className="text-2xl font-bold">{article.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          {article.author && <span>By {article.author}</span>}
          {article.published_at && (
            <span>{formatDateTime(article.published_at)}</span>
          )}
          <span>Fetched {formatDateTime(article.fetched_at)}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <a href={article.url} target="_blank" rel="noopener noreferrer">
          <Button variant="outline" size="sm">
            <ExternalLink className="mr-2 h-4 w-4" />
            Open Original
          </Button>
        </a>
        <Button
          variant="outline"
          size="sm"
          onClick={handleSummarize}
          disabled={isSummarizing}
        >
          {isSummarizing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="mr-2 h-4 w-4" />
          )}
          {article.summary ? "Re-summarize" : "Generate Summary"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleIngest}
          disabled={isIngesting}
        >
          {isIngesting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Upload className="mr-2 h-4 w-4" />
          )}
          Ingest to Qdrant
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDelete}
          disabled={isDeleting}
          className="text-destructive"
        >
          {isDeleting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="mr-2 h-4 w-4" />
          )}
          Delete
        </Button>
      </div>

      {article.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              AI Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{article.summary}</p>
          </CardContent>
        </Card>
      )}

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Content</CardTitle>
        </CardHeader>
        <CardContent>
          {article.content ? (
            <div className="prose prose-sm max-w-none whitespace-pre-wrap">
              {article.content}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No content available for this article.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
