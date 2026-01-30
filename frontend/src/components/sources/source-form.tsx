"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";
import type { SourceResponse, SourceCreate, SourceType } from "@/types/api";

interface SourceFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: SourceCreate) => Promise<void>;
  source?: SourceResponse | null;
}

export function SourceForm({
  open,
  onOpenChange,
  onSubmit,
  source,
}: SourceFormProps) {
  const [name, setName] = useState(source?.name ?? "");
  const [url, setUrl] = useState(source?.url ?? "");
  const [description, setDescription] = useState(source?.description ?? "");
  const [sourceType, setSourceType] = useState<SourceType>(
    source?.source_type ?? "static"
  );
  const [isActive, setIsActive] = useState(source?.is_active ?? true);
  const [sourceConfig, setSourceConfig] = useState(
    source?.source_config ? JSON.stringify(source.source_config, null, 2) : "{}"
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    let parsedConfig: Record<string, unknown>;
    try {
      parsedConfig = JSON.parse(sourceConfig);
    } catch {
      setError("Source config must be valid JSON");
      setIsLoading(false);
      return;
    }

    try {
      await onSubmit({
        name,
        url: url || undefined,
        description: description || undefined,
        source_type: sourceType,
        is_active: isActive,
        source_config: parsedConfig,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save source");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{source ? "Edit Source" : "Add Source"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="BBC News"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="url">URL</Label>
            <Input
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://bbc.com"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="British news source"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="source_type">Source Type</Label>
            <Select
              value={sourceType}
              onValueChange={(v) => setSourceType(v as SourceType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="rss">RSS Feed</SelectItem>
                <SelectItem value="newsapi">NewsAPI</SelectItem>
                <SelectItem value="static">Static</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="source_config">Source Config (JSON)</Label>
            <Textarea
              id="source_config"
              value={sourceConfig}
              onChange={(e) => setSourceConfig(e.target.value)}
              rows={4}
              className="font-mono text-sm"
              placeholder='{"feed_url": "https://..."}'
            />
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="is_active"
              checked={isActive}
              onCheckedChange={(checked) => setIsActive(checked === true)}
            />
            <Label htmlFor="is_active">Active</Label>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {source ? "Update" : "Create"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
