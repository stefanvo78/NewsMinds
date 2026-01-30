"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import * as api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SourceTable } from "@/components/sources/source-table";
import { SourceForm } from "@/components/sources/source-form";
import { Loader2, Plus, RefreshCw } from "lucide-react";
import type { SourceResponse, SourceCreate } from "@/types/api";

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCollecting, setIsCollecting] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const fetchSources = async () => {
    try {
      setIsLoading(true);
      const data = await api.listSources();
      setSources(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load sources");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleCreate = async (data: SourceCreate) => {
    await api.createSource(data);
    toast.success("Source created");
    await fetchSources();
  };

  const handleCollectAll = async () => {
    setIsCollecting(true);
    try {
      const result = await api.collectAll();
      toast.success(
        `Collected ${result.articles_stored} articles from ${result.sources_processed} sources`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Collection failed");
    } finally {
      setIsCollecting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sources</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCollectAll} disabled={isCollecting}>
            {isCollecting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Collect All
          </Button>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Source
          </Button>
        </div>
      </div>

      <SourceTable sources={sources} onRefresh={fetchSources} />

      <SourceForm
        open={showCreate}
        onOpenChange={setShowCreate}
        onSubmit={handleCreate}
      />
    </div>
  );
}
