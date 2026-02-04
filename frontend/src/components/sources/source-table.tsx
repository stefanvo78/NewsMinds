"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import * as api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { SourceForm } from "./source-form";
import { Loader2, Pencil, Play, Trash2 } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { SourceResponse, SourceCreate } from "@/types/api";

interface SourceTableProps {
  sources: SourceResponse[];
  onRefresh: () => Promise<void>;
}

export function SourceTable({ sources, onRefresh }: SourceTableProps) {
  const [editingSource, setEditingSource] = useState<SourceResponse | null>(null);
  const [deletingSource, setDeletingSource] = useState<SourceResponse | null>(null);
  const [collectingIds, setCollectingIds] = useState<Set<string>>(new Set());
  const pollRefs = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  const stopPolling = useCallback((sourceId: string) => {
    const interval = pollRefs.current.get(sourceId);
    if (interval) {
      clearInterval(interval);
      pollRefs.current.delete(sourceId);
    }
  }, []);

  const stopAllPolling = useCallback(() => {
    pollRefs.current.forEach((interval) => clearInterval(interval));
    pollRefs.current.clear();
  }, []);

  // Clean up all polling on unmount
  useEffect(() => {
    return stopAllPolling;
  }, [stopAllPolling]);

  const startPolling = useCallback(
    (sourceId: string) => {
      stopPolling(sourceId);
      const interval = setInterval(async () => {
        try {
          const status = await api.getSourceCollectionStatus(sourceId);
          if (!status.running) {
            stopPolling(sourceId);
            setCollectingIds((prev) => {
              const next = new Set(prev);
              next.delete(sourceId);
              return next;
            });
            if (status.error) {
              toast.error(`Collection failed: ${status.error}`);
            } else if (status.result) {
              toast.success(
                `Collected ${status.result.new} new articles from ${status.result.source}`
              );
            }
            onRefresh();
          }
        } catch {
          // ignore polling errors
        }
      }, 3000);
      pollRefs.current.set(sourceId, interval);
    },
    [stopPolling, onRefresh]
  );

  const handleUpdate = async (data: SourceCreate) => {
    if (!editingSource) return;
    await api.updateSource(editingSource.id, data);
    toast.success("Source updated");
    await onRefresh();
  };

  const handleDelete = async () => {
    if (!deletingSource) return;
    try {
      await api.deleteSource(deletingSource.id);
      toast.success("Source deleted");
      await onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingSource(null);
    }
  };

  const handleCollect = async (source: SourceResponse) => {
    setCollectingIds((prev) => new Set(prev).add(source.id));
    try {
      await api.collectSource(source.id);
      toast.info(`Collection started for '${source.name}'...`);
      startPolling(source.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Collection failed");
      setCollectingIds((prev) => {
        const next = new Set(prev);
        next.delete(source.id);
        return next;
      });
    }
  };

  const typeVariant = (type: string) => {
    switch (type) {
      case "rss":
        return "default" as const;
      case "newsapi":
        return "secondary" as const;
      default:
        return "outline" as const;
    }
  };

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>URL</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sources.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                No sources yet. Add one to get started.
              </TableCell>
            </TableRow>
          ) : (
            sources.map((source) => (
              <TableRow key={source.id}>
                <TableCell className="font-medium">{source.name}</TableCell>
                <TableCell>
                  <Badge variant={typeVariant(source.source_type)}>
                    {source.source_type}
                  </Badge>
                </TableCell>
                <TableCell className="max-w-48 truncate text-muted-foreground">
                  {source.url || "-"}
                </TableCell>
                <TableCell>
                  <Badge variant={source.is_active ? "default" : "outline"}>
                    {source.is_active ? "Active" : "Inactive"}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground whitespace-nowrap">
                  {formatDate(source.created_at)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    {source.source_type !== "static" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCollect(source)}
                        disabled={collectingIds.has(source.id)}
                        title="Collect articles"
                      >
                        {collectingIds.has(source.id) ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditingSource(source)}
                      title="Edit source"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeletingSource(source)}
                      title="Delete source"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <SourceForm
        open={!!editingSource}
        onOpenChange={(open) => !open && setEditingSource(null)}
        onSubmit={handleUpdate}
        source={editingSource}
      />

      <AlertDialog
        open={!!deletingSource}
        onOpenChange={(open) => !open && setDeletingSource(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete source?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete &quot;{deletingSource?.name}&quot;. This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
