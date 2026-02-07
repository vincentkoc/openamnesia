import { IconSearch } from "./Icons";
import { cn } from "../../lib/utils";

export function FilterInput({
  value,
  onChange,
  placeholder = "filter...",
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-1 rounded border border-line/50 bg-void-1/50 px-2", className)}>
      <IconSearch size={11} className="shrink-0 text-text-3" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-[22px] w-[120px] bg-transparent font-mono text-[10px] text-text-1 placeholder:text-text-3/50 focus:outline-none"
      />
      {value && (
        <button
          onClick={() => onChange("")}
          className="text-[10px] text-text-3 hover:text-text-1"
        >
          &times;
        </button>
      )}
    </div>
  );
}
