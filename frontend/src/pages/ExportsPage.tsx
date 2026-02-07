import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { ExportFileEntry, SkillFileEntry } from "../lib/api";
import { cn } from "../lib/utils";
import { EmptyState } from "../components/common/EmptyState";
import { IconChevronDown, IconChevronRight } from "../components/common/Icons";
import { useState } from "react";

type Period = "daily" | "weekly" | "monthly" | "all";

export function ExportsPage() {
  const [period, setPeriod] = useState<Period>("daily");
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const { data: listing } = useQuery({
    queryKey: ["exports"],
    queryFn: api.exports,
  });

  // Filter memory files by period
  const memoryFiles = (listing?.memory ?? []).filter((f) => {
    if (period === "all") return true;
    return f.type === period;
  });

  const skillFiles = listing?.skills ?? [];
  const config = listing?.config;

  function copyToClipboard(text: string, label: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopyFeedback(label);
      setTimeout(() => setCopyFeedback(null), 2000);
    });
  }

  return (
    <div className="flex h-full flex-col">
      {/* Control bar */}
      <div className="flex shrink-0 items-center gap-3 border-b border-line/30 px-4 py-1.5">
        <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.1em] text-text-0">Exports</span>

        <div className="toggle-group">
          {(["daily", "weekly", "monthly", "all"] as Period[]).map((p) => (
            <button key={p} className={period === p ? "active" : ""} onClick={() => setPeriod(p)}>{p}</button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <span className="font-mono text-[9px] tabular-nums text-text-3">
            {memoryFiles.length} files
          </span>
        </div>
      </div>

      {/* Config info */}
      {config && (
        <div className="flex shrink-0 items-center gap-4 border-b border-line/20 bg-void-1/30 px-4 py-1.5">
          <div className="flex items-center gap-4 font-mono text-[9px] text-text-3">
            <span>memory: <span className="text-text-2">{config.memory_dir}</span></span>
            <span>skills: <span className="text-text-2">{config.skills_dir}</span></span>
            <span>mode: <span className="text-text-2">{config.mode}</span></span>
            <span>formats: <span className="text-text-2">{config.formats.join(", ")}</span></span>
          </div>
        </div>
      )}

      {/* File listing */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {memoryFiles.length > 0 ? (
          <div>
            {memoryFiles.map((file) => (
              <ExportFileRow
                key={file.filename}
                file={file}
                expanded={expandedFile === file.filename}
                onToggle={() => setExpandedFile(expandedFile === file.filename ? null : file.filename)}
                onCopy={copyToClipboard}
                copyFeedback={copyFeedback}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="No exports yet" description="Exports appear as the pipeline processes events. Check config.yaml to configure." icon="default" />
        )}

        {/* Skills section */}
        {skillFiles.length > 0 && (
          <div className="mt-2">
            <div className="section-rule gap-0">
              <span className="min-w-0 flex-1">skill exports</span>
            </div>
            {skillFiles.map((sf) => (
              <SkillFileRow
                key={sf.filename}
                file={sf}
                expanded={expandedSkill === sf.filename}
                onToggle={() => setExpandedSkill(expandedSkill === sf.filename ? null : sf.filename)}
                onCopy={copyToClipboard}
                copyFeedback={copyFeedback}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ExportFileRow({ file, expanded, onToggle, onCopy, copyFeedback }: {
  file: ExportFileEntry;
  expanded: boolean;
  onToggle: () => void;
  onCopy: (text: string, label: string) => void;
  copyFeedback: string | null;
}) {
  const { data: content } = useQuery({
    queryKey: ["export-memory", file.filename],
    queryFn: () => api.exportMemoryFile(file.filename),
    enabled: expanded,
  });

  const typeLabel = file.type === "daily" ? "D" : file.type === "weekly" ? "W" : file.type === "monthly" ? "M" : "?";
  const typeColor = file.type === "daily" ? "text-ok" : file.type === "weekly" ? "text-accent" : file.type === "monthly" ? "text-warn" : "text-text-3";

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onToggle(); } }}
        className={cn("data-row cursor-pointer", expanded && "selected")}
      >
        <span className="flex w-[24px] shrink-0 items-center justify-center">
          {expanded ? <IconChevronDown size={12} className="text-text-2" /> : <IconChevronRight size={12} className="text-text-3" />}
        </span>
        <span className={cn("w-[24px] shrink-0 text-center font-mono text-[10px] font-bold", typeColor)}>{typeLabel}</span>
        <span className="font-mono text-[11px] font-medium text-text-0">{file.date}</span>
        <span className="ml-auto flex items-center gap-3">
          <span className="font-mono text-[9px] tabular-nums text-text-3">{formatSize(file.size)}</span>
          <span className="font-mono text-[9px] text-text-3">{file.filename}</span>
          {content && (
            <button
              onClick={(e) => { e.stopPropagation(); onCopy(content.content, file.filename); }}
              className="rounded border border-line/40 px-1.5 py-0.5 font-sans text-[8px] font-medium uppercase tracking-wider text-text-3 transition-colors hover:bg-void-2 hover:text-text-1"
            >
              {copyFeedback === file.filename ? "copied!" : "copy md"}
            </button>
          )}
        </span>
      </div>

      {expanded && content && (
        <div className="border-b border-line/20 bg-void-1/30 px-6 py-3">
          <pre className="whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-text-1">{content.content}</pre>
        </div>
      )}
      {expanded && !content && (
        <div className="border-b border-line/20 bg-void-1/30 px-6 py-3">
          <span className="font-mono text-[10px] text-text-3">loading...</span>
        </div>
      )}
    </div>
  );
}

function SkillFileRow({ file, expanded, onToggle, onCopy, copyFeedback }: {
  file: SkillFileEntry;
  expanded: boolean;
  onToggle: () => void;
  onCopy: (text: string, label: string) => void;
  copyFeedback: string | null;
}) {
  const { data: content } = useQuery({
    queryKey: ["export-skill", file.filename],
    queryFn: () => api.exportSkillFile(file.filename),
    enabled: expanded,
  });

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onToggle(); } }}
        className={cn("data-row cursor-pointer", expanded && "selected")}
      >
        <span className="flex w-[24px] shrink-0 items-center justify-center">
          {expanded ? <IconChevronDown size={12} className="text-text-2" /> : <IconChevronRight size={12} className="text-text-3" />}
        </span>
        <span className="font-mono text-[11px] font-medium text-text-0">{file.filename}</span>
        <span className="ml-auto flex items-center gap-3">
          <span className="font-mono text-[9px] tabular-nums text-text-3">{formatSize(file.size)}</span>
          {content && (
            <button
              onClick={(e) => { e.stopPropagation(); onCopy(content.content, file.filename); }}
              className="rounded border border-line/40 px-1.5 py-0.5 font-sans text-[8px] font-medium uppercase tracking-wider text-text-3 transition-colors hover:bg-void-2 hover:text-text-1"
            >
              {copyFeedback === file.filename ? "copied!" : "copy md"}
            </button>
          )}
        </span>
      </div>

      {expanded && content && (
        <div className="border-b border-line/20 bg-void-1/30 px-6 py-3">
          <pre className="whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-text-1">{content.content}</pre>
        </div>
      )}
      {expanded && !content && (
        <div className="border-b border-line/20 bg-void-1/30 px-6 py-3">
          <span className="font-mono text-[10px] text-text-3">loading...</span>
        </div>
      )}
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  return `${(bytes / 1024).toFixed(1)}K`;
}
