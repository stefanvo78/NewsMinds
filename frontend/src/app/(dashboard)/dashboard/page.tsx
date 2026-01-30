"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import * as api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentArticles } from "@/components/dashboard/recent-articles";
import { Loader2, RefreshCw } from "lucide-react";
import type { SourceResponse, ArticleResponse } from "@/types/api";

export default function DashboardPage() {
  const [sources, setSources] = useState<SourceResponse[]>([]);
  const [articles, setArticles] = useState<ArticleResponse[]>([]);
  const [totalArticles, setTotalArticles] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isCollecting, setIsCollecting] = useState(false);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [sourcesData, articlesData] = await Promise.all([
        api.listSources(),
        api.listArticles({ page: 1, per_page: 5 }),
      ]);
      setSources(sourcesData);
      setArticles(articlesData.items);
      setTotalArticles(articlesData.total);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCollectAll = async () => {
    setIsCollecting(true);
    try {
      const result = await api.collectAll();
      toast.success(
        `Collected ${result.articles_stored} new articles from ${result.sources_processed} sources`
      );
      await fetchData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Collection failed");
    } finally {
      setIsCollecting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const activeSources = sources.filter((s) => s.is_active).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Button onClick={handleCollectAll} disabled={isCollecting}>
          {isCollecting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Collect All Sources
        </Button>
      </div>

      <StatsCards
        totalSources={sources.length}
        activeSources={activeSources}
        totalArticles={totalArticles}
      />

      <RecentArticles articles={articles} />
    </div>
  );
}
