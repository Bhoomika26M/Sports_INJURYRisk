"use client";

import { useState, useRef, useEffect } from "react";
import { Icon, type IconName } from "@/components/icons";

export interface MovementOption {
  code: string;
  name: string;
  description: string;
  icon: IconName;
}

export const MOVEMENT_DISCIPLINES: MovementOption[] = [
  {
    code: "auto",
    name: "Auto-Detect from Footage",
    description: "AI recognizes movement signatures, camera angle, and kinetic phase",
    icon: "sparkles",
  },
  {
    code: "squatting",
    name: "Squatting",
    description: "Barbell back squat, goblet squat, bodyweight sitting turnaround",
    icon: "activity",
  },
  {
    code: "running",
    name: "Running / Sprinting",
    description: "Sprint mechanics, treadmill gait, peak stride separation",
    icon: "zap",
  },
  {
    code: "jumping",
    name: "Jumping / Landing",
    description: "Drop vertical jump, box landing, ground impact shock absorption",
    icon: "target",
  },
  {
    code: "cutting",
    name: "Cutting / Change of Direction",
    description: "Deceleration plant step, lateral agility, 45° to 180° cut mechanics",
    icon: "shield",
  },
  {
    code: "throwing",
    name: "Throwing / Overhead",
    description: "Shot put, baseball pitch, overhead throw release extension",
    icon: "lightbulb",
  },
];

interface CustomMovementSelectProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

export function CustomMovementSelect({
  value,
  onChange,
  label = "Movement Discipline",
}: CustomMovementSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected =
    MOVEMENT_DISCIPLINES.find((m) => m.code === value) || MOVEMENT_DISCIPLINES[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1.5 w-full">
      {label && (
        <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
          {label}
        </label>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between w-full h-11 px-3.5 rounded-xl border bg-white transition-all text-left cursor-pointer shadow-2xs ${
          isOpen
            ? "border-brand-dark ring-2 ring-brand-light/60 shadow-sm"
            : "border-slate-300 hover:border-slate-400"
        }`}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-light/60 text-brand-dark shrink-0">
            <Icon name={selected.icon} className="h-4 w-4" />
          </span>
          <div className="truncate">
            <span className="text-xs font-bold text-slate-900 block truncate">
              {selected.name}
            </span>
          </div>
        </div>

        <span
          className={`text-slate-400 transition-transform duration-200 shrink-0 ml-2 ${
            isOpen ? "rotate-180 text-brand-dark" : ""
          }`}
        >
          <Icon name="chevron-down" className="h-4 w-4" />
        </span>
      </button>

      {/* Floating Menu Popover */}
      {isOpen && (
        <div className="absolute top-[100%] left-0 right-0 z-50 mt-1.5 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl animate-in fade-in zoom-in-95 duration-100">
          <div className="flex flex-col gap-1 max-h-72 overflow-y-auto">
            {MOVEMENT_DISCIPLINES.map((item) => {
              const isSelected = item.code === value;
              return (
                <button
                  key={item.code}
                  type="button"
                  onClick={() => {
                    onChange(item.code);
                    setIsOpen(false);
                  }}
                  className={`flex items-center justify-between rounded-xl px-3 py-2.5 text-left transition-all cursor-pointer ${
                    isSelected
                      ? "bg-brand-light/30 text-brand-dark font-bold"
                      : "hover:bg-slate-50 text-slate-800"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className={`flex h-8 w-8 items-center justify-center rounded-lg shrink-0 ${
                        isSelected
                          ? "bg-brand-dark text-white"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      <Icon name={item.icon} className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-bold leading-snug truncate">
                        {item.name}
                      </p>
                      <p className="text-[11px] text-slate-500 line-clamp-1 leading-normal font-normal">
                        {item.description}
                      </p>
                    </div>
                  </div>

                  {isSelected && (
                    <span className="text-brand-dark shrink-0 ml-2">
                      <Icon name="check" className="h-4 w-4" />
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
