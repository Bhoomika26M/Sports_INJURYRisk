"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { Icon } from "@/components/icons";
import { movementLabel } from "@/lib/format";
import { AuthThumbnail } from "@/components/auth-media";
import type { BenchmarkPreset, Video } from "@/lib/types";

export interface CustomVideoSelectOption {
  id: string;
  title: string;
  movement_type: string;
  camera_view?: string;
  duration_seconds?: number | null;
  is_preset?: boolean;
  is_textbook?: boolean;
}

interface CustomVideoSelectProps {
  label: string;
  value: string;
  onChange: (val: string) => void;
  presets: BenchmarkPreset[];
  videos: Video[];
  placeholder?: string;
}

export function CustomVideoSelect({
  label,
  value,
  onChange,
  presets,
  videos,
  placeholder = "Choose a movement clip...",
}: CustomVideoSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Build unified options
  const presetOptions: CustomVideoSelectOption[] = useMemo(() => {
    return presets.map((p) => ({
      id: p.id,
      title: p.title,
      movement_type: p.movement_type,
      camera_view: p.camera_view,
      duration_seconds: p.duration_seconds,
      is_preset: true,
      is_textbook: p.is_textbook,
    }));
  }, [presets]);

  const videoOptions: CustomVideoSelectOption[] = useMemo(() => {
    return videos.map((v) => ({
      id: v.id,
      title: `${movementLabel(v.movement_type)} · ${v.original_filename || v.id.slice(0, 8)}`,
      movement_type: v.movement_type,
      camera_view: v.camera_view,
      duration_seconds: v.duration_seconds ?? undefined,
      is_preset: false,
    }));
  }, [videos]);

  const selectedOption = useMemo(() => {
    return (
      presetOptions.find((o) => o.id === value) ||
      videoOptions.find((o) => o.id === value) ||
      null
    );
  }, [value, presetOptions, videoOptions]);

  // Filter options by search keyword
  const filteredPresets = useMemo(() => {
    if (!search.trim()) return presetOptions;
    const q = search.toLowerCase();
    return presetOptions.filter(
      (o) =>
        o.title.toLowerCase().includes(q) ||
        o.movement_type.toLowerCase().includes(q) ||
        (o.camera_view && o.camera_view.toLowerCase().includes(q))
    );
  }, [presetOptions, search]);

  const filteredVideos = useMemo(() => {
    if (!search.trim()) return videoOptions;
    const q = search.toLowerCase();
    return videoOptions.filter(
      (o) =>
        o.title.toLowerCase().includes(q) ||
        o.movement_type.toLowerCase().includes(q) ||
        (o.camera_view && o.camera_view.toLowerCase().includes(q))
    );
  }, [videoOptions, search]);

  return (
    <div className="flex flex-col gap-2 relative" ref={dropdownRef}>
      <label className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center justify-between">
        <span>{label}</span>
        {selectedOption && (
          <span className="text-[11px] font-medium text-brand-dark bg-brand-light/40 px-2 py-0.5 rounded-md">
            {movementLabel(selectedOption.movement_type)}
          </span>
        )}
      </label>

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`w-full min-h-[50px] px-4 py-2.5 rounded-xl border bg-white flex items-center justify-between gap-3 text-left transition-all shadow-2xs cursor-pointer ${
          isOpen
            ? "border-brand-dark ring-2 ring-brand/15"
            : "border-slate-200/90 hover:border-slate-300"
        }`}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm ${
              selectedOption?.is_preset
                ? "bg-amber-100 text-amber-700"
                : selectedOption
                ? "bg-brand-light text-brand-dark"
                : "bg-slate-100 text-slate-400"
            }`}
          >
            {selectedOption?.is_preset ? (
              <Icon name="star" className="h-4 w-4 text-amber-600" />
            ) : selectedOption ? (
              <Icon name="video" className="h-4 w-4 text-brand-dark" />
            ) : (
              <Icon name="folder" className="h-4 w-4 text-slate-400" />
            )}
          </div>

          {selectedOption ? (
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-900 truncate">
                {selectedOption.title}
              </p>
              <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                <span>{movementLabel(selectedOption.movement_type)}</span>
                {selectedOption.camera_view && (
                  <>
                    <span>•</span>
                    <span className="capitalize">{selectedOption.camera_view} View</span>
                  </>
                )}
                {selectedOption.duration_seconds && (
                  <>
                    <span>•</span>
                    <span>{selectedOption.duration_seconds.toFixed(1)}s</span>
                  </>
                )}
              </div>
            </div>
          ) : (
            <span className="text-sm text-slate-400 font-normal">{placeholder}</span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0 text-slate-400">
          <Icon
            name="chevron-down"
            className={`h-4 w-4 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          />
        </div>
      </button>

      {/* Dropdown Menu Popover */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 z-50 mt-1.5 rounded-2xl border border-slate-200 bg-white shadow-xl max-h-84 overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-150">
          {/* Search Input Filter */}
          <div className="p-2.5 border-b border-slate-100 bg-slate-50/70">
            <div className="relative flex items-center">
              <span className="absolute left-2.5 text-slate-400 pointer-events-none">
                <Icon name="search" className="h-3.5 w-3.5" />
              </span>
              <input
                type="text"
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by movement, clip title, or angle..."
                className="w-full pl-8 pr-7 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-brand-dark focus:ring-1 focus:ring-brand"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  className="absolute right-2 text-slate-400 hover:text-slate-600 cursor-pointer"
                >
                  <Icon name="x" className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Options List */}
          <div className="overflow-y-auto p-1.5 space-y-3 max-h-70">
            {/* Group 1: Presets */}
            {filteredPresets.length > 0 && (
              <div>
                <p className="px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50/70 rounded-md mb-1 flex items-center gap-1.5">
                  <Icon name="star" className="h-3.5 w-3.5 text-amber-600" />
                  <span>Pre-Loaded Benchmark Standards</span>
                </p>
                <div className="space-y-0.5">
                  {filteredPresets.map((opt) => {
                    const isSelected = opt.id === value;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => {
                          onChange(opt.id);
                          setIsOpen(false);
                          setSearch("");
                        }}
                        className={`w-full px-3 py-2 rounded-xl text-left flex items-center justify-between gap-2 transition-all cursor-pointer ${
                          isSelected
                            ? "bg-brand-light/50 text-brand-dark font-semibold"
                            : "hover:bg-slate-50 text-slate-800"
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold truncate">{opt.title}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1.5">
                            <span className="capitalize">{opt.movement_type}</span>
                            {opt.camera_view && <span>• {opt.camera_view}</span>}
                            {opt.duration_seconds && <span>• {opt.duration_seconds.toFixed(1)}s</span>}
                            {opt.is_textbook && (
                              <span className="text-[10px] bg-sky-100 text-sky-700 font-bold px-1.5 py-0.2 rounded">
                                Textbook 3D Model
                              </span>
                            )}
                          </p>
                        </div>
                        {isSelected && (
                          <Icon name="check" className="h-4 w-4 text-brand-dark shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Group 2: Uploaded Videos */}
            {filteredVideos.length > 0 && (
              <div>
                <p className="px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-600 bg-slate-100/80 rounded-md mb-1 flex items-center gap-1.5">
                  <Icon name="video" className="h-3.5 w-3.5 text-slate-600" />
                  <span>Analyzed Videos in Database</span>
                </p>
                <div className="space-y-0.5">
                  {filteredVideos.map((opt) => {
                    const isSelected = opt.id === value;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => {
                          onChange(opt.id);
                          setIsOpen(false);
                          setSearch("");
                        }}
                        className={`w-full px-3 py-2 rounded-xl text-left flex items-center justify-between gap-2 transition-all cursor-pointer ${
                          isSelected
                            ? "bg-brand-light/50 text-brand-dark font-semibold"
                            : "hover:bg-slate-50 text-slate-800"
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold truncate">{opt.title}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1.5">
                            <span className="capitalize">{movementLabel(opt.movement_type)}</span>
                            {opt.camera_view && <span>• {opt.camera_view} view</span>}
                            {opt.duration_seconds && <span>• {opt.duration_seconds.toFixed(1)}s</span>}
                          </p>
                        </div>
                        {isSelected && (
                          <Icon name="check" className="h-4 w-4 text-brand-dark shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {filteredPresets.length === 0 && filteredVideos.length === 0 && (
              <div className="p-6 text-center text-xs text-slate-400">
                No matching clips found for &ldquo;{search}&rdquo;
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Instant Video Selection Preview Card
 * Displays real-time thumbnail or textbook badge before benchmark execution.
 */
export function VideoSelectionPreview({
  option,
  label,
}: {
  option: CustomVideoSelectOption | null;
  label: string;
}) {
  if (!option) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-6 flex flex-col items-center justify-center text-center min-h-[140px]">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-400 mb-2">
          <Icon name="video" className="h-5 w-5" />
        </div>
        <p className="text-xs font-semibold text-slate-500">No {label} Selected</p>
        <p className="text-[11px] text-slate-400 mt-0.5">
          Choose a clip above to preview kinematics
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-xs flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
          {label} Preview
        </span>
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span>Ready for Benchmark</span>
        </span>
      </div>

      <div className="flex items-start gap-3">
        {/* Real Thumbnail from DB or Textbook Model */}
        <div className="w-24 h-18 shrink-0 rounded-xl overflow-hidden bg-slate-100 border border-slate-200 flex items-center justify-center relative">
          {option.is_textbook ? (
            <div className="flex flex-col items-center justify-center text-center p-2 bg-gradient-to-br from-brand-light/30 to-surface w-full h-full">
              <Icon name="target" className="h-5 w-5 text-brand-dark mb-1" />
              <span className="text-[9px] font-bold text-slate-700 uppercase">
                Textbook
              </span>
            </div>
          ) : (
            <AuthThumbnail
              path={`/videos/${option.id}/thumbnail`}
              alt={option.title}
              className="w-full h-full object-cover"
            />
          )}
        </div>

        {/* Details & Specs */}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold text-slate-900 truncate">
            {option.title}
          </p>

          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md">
              {movementLabel(option.movement_type)}
            </span>
            {option.camera_view && (
              <span className="text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md capitalize">
                {option.camera_view} View
              </span>
            )}
            {option.duration_seconds && (
              <span className="text-slate-500">
                {option.duration_seconds.toFixed(1)}s
              </span>
            )}
          </div>

          <p className="text-[10px] text-slate-400 mt-1 italic">
            {option.is_textbook
              ? "Synthesized from gold-standard clinical motion analysis."
              : "Capture frame extracted from video."}
          </p>
        </div>
      </div>
    </div>
  );
}
