"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

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

  // Check if a collection is already running on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await api.getCollectionStatus();
        if (status.running) {
          setIsCollecting(true);
          startPolling();
        }
      } catch {
        // ignore - status endpoint may not exist yet
      }
    };
    fetchSources();
    checkStatus();
    return stopPolling;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getCollectionStatus();
        if (!status.running) {
          stopPolling();
          setIsCollecting(false);
          if (status.error) {
            toast.error(`Collection failed: ${status.error}`);
          } else if (status.result) {
            toast.success(
              `Collected ${status.result.total_new} new articles from ${status.result.sources_processed} sources`
            );
          }
          // Refresh sources list after collection
          fetchSources();
        }
      } catch {
        // ignore polling errors
      }
    }, 3000);
  }, [stopPolling]);

  const handleCreate = async (data: SourceCreate) => {
    await api.createSource(data);
    toast.success("Source created");
    await fetchSources();
  };

  const handleCollectAll = async () => {
    setIsCollecting(true);
    try {
      await api.collectAll();
      toast.info("Collection started in background...");
      startPolling();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start collection");
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
            {isCollecting ? "Collecting..." : "Collect All"}
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
