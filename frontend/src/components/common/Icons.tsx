import type { SVGProps } from "react";

interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number;
}

function I({ size = 16, children, ...props }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {children}
    </svg>
  );
}

export function IconBrain(props: IconProps) {
  return (
    <I {...props}>
      <path d="M8 2C6 2 4.5 3.2 4.5 5c0 .8-.8 1.2-1.2 2-.6 1-.3 2.5.7 3.3.5.4.5 1 .5 1.7 0 1 1 2 2.5 2h2c1.5 0 2.5-1 2.5-2 0-.7 0-1.3.5-1.7 1-.8 1.3-2.3.7-3.3-.4-.8-1.2-1.2-1.2-2C11.5 3.2 10 2 8 2z" />
      <path d="M6.5 7.5c0-1 .7-1.5 1.5-1.5s1.5.5 1.5 1.5" />
      <line x1="8" y1="10" x2="8" y2="14" />
    </I>
  );
}

export function IconDatabase(props: IconProps) {
  return (
    <I {...props}>
      <ellipse cx="8" cy="4" rx="5" ry="2" />
      <path d="M3 4v8c0 1.1 2.2 2 5 2s5-.9 5-2V4" />
      <path d="M3 8c0 1.1 2.2 2 5 2s5-.9 5-2" />
    </I>
  );
}

export function IconClock(props: IconProps) {
  return (
    <I {...props}>
      <circle cx="8" cy="8" r="6" />
      <polyline points="8,4 8,8 11,10" />
    </I>
  );
}

export function IconFilter(props: IconProps) {
  return (
    <I {...props}>
      <polygon points="2,3 14,3 9,9 9,13 7,14 7,9" />
    </I>
  );
}

export function IconSearch(props: IconProps) {
  return (
    <I {...props}>
      <circle cx="7" cy="7" r="4.5" />
      <line x1="10.5" y1="10.5" x2="14" y2="14" />
    </I>
  );
}

export function IconGrid(props: IconProps) {
  return (
    <I {...props}>
      <rect x="2" y="2" width="5" height="5" rx="0.5" />
      <rect x="9" y="2" width="5" height="5" rx="0.5" />
      <rect x="2" y="9" width="5" height="5" rx="0.5" />
      <rect x="9" y="9" width="5" height="5" rx="0.5" />
    </I>
  );
}

export function IconList(props: IconProps) {
  return (
    <I {...props}>
      <line x1="5" y1="4" x2="14" y2="4" />
      <line x1="5" y1="8" x2="14" y2="8" />
      <line x1="5" y1="12" x2="14" y2="12" />
      <circle cx="2.5" cy="4" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="2.5" cy="8" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="2.5" cy="12" r="0.8" fill="currentColor" stroke="none" />
    </I>
  );
}

export function IconChevronLeft(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="10,3 5,8 10,13" />
    </I>
  );
}

export function IconChevronRight(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="6,3 11,8 6,13" />
    </I>
  );
}

export function IconChevronDown(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="3,6 8,11 13,6" />
    </I>
  );
}

export function IconChevronUp(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="3,10 8,5 13,10" />
    </I>
  );
}

export function IconSettings(props: IconProps) {
  return (
    <I {...props}>
      <line x1="2" y1="4" x2="14" y2="4" />
      <line x1="2" y1="8" x2="14" y2="8" />
      <line x1="2" y1="12" x2="14" y2="12" />
      <circle cx="5" cy="4" r="1.5" fill="var(--bg, #0C0C12)" />
      <circle cx="10" cy="8" r="1.5" fill="var(--bg, #0C0C12)" />
      <circle cx="7" cy="12" r="1.5" fill="var(--bg, #0C0C12)" />
    </I>
  );
}

export function IconRefresh(props: IconProps) {
  return (
    <I {...props}>
      <path d="M13.5 3A6.5 6.5 0 0 0 3 5.5" />
      <polyline points="13.5,0.5 13.5,3.5 10.5,3.5" />
      <path d="M2.5 13A6.5 6.5 0 0 0 13 10.5" />
      <polyline points="2.5,15.5 2.5,12.5 5.5,12.5" />
    </I>
  );
}

export function IconActivity(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="1,8 4,8 5.5,3 7.5,13 9.5,6 11,10 12,8 15,8" />
    </I>
  );
}

export function IconTerminal(props: IconProps) {
  return (
    <I {...props}>
      <rect x="1.5" y="2.5" width="13" height="11" rx="1.5" />
      <polyline points="4.5,6 7,8.5 4.5,11" />
      <line x1="9" y1="11" x2="11.5" y2="11" />
    </I>
  );
}

export function IconCode(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="5,4 1,8 5,12" />
      <polyline points="11,4 15,8 11,12" />
      <line x1="9.5" y1="2.5" x2="6.5" y2="13.5" />
    </I>
  );
}

export function IconMessage(props: IconProps) {
  return (
    <I {...props}>
      <path d="M2 3h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H5l-3 3V4a1 1 0 0 1 1-1z" />
    </I>
  );
}

export function IconPlay(props: IconProps) {
  return (
    <I {...props}>
      <polygon points="4,2 14,8 4,14" fill="currentColor" stroke="none" />
    </I>
  );
}

export function IconCheck(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="3,8 6.5,12 13,4" />
    </I>
  );
}

export function IconX(props: IconProps) {
  return (
    <I {...props}>
      <line x1="4" y1="4" x2="12" y2="12" />
      <line x1="12" y1="4" x2="4" y2="12" />
    </I>
  );
}

export function IconExpand(props: IconProps) {
  return (
    <I {...props}>
      <polyline points="10,2 14,2 14,6" />
      <polyline points="6,14 2,14 2,10" />
      <line x1="14" y1="2" x2="9.5" y2="6.5" />
      <line x1="2" y1="14" x2="6.5" y2="9.5" />
    </I>
  );
}

export function IconZap(props: IconProps) {
  return (
    <I {...props}>
      <polygon points="9,1 3,9 8,9 7,15 13,7 8,7" fill="currentColor" stroke="none" />
    </I>
  );
}

export function IconExport(props: IconProps) {
  return (
    <I {...props}>
      <path d="M4 13h8M8 3v7M5 6l3-3 3 3" />
    </I>
  );
}

/** Brain-meets-defrag logo: 7x7 pixel grid forming brain silhouette */
export function IconDefragLogo({ size = 16, ...props }: IconProps) {
  // 7x7 grid, 1=filled block, 0=empty
  const grid = [
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 0, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 0, 1, 0, 1, 1],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 0, 1, 0, 0],
  ];
  const cell = 2;
  const gap = 0.3;
  const offset = 0.5;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      {...props}
    >
      {grid.map((row, y) =>
        row.map((v, x) =>
          v ? (
            <rect
              key={`${x}-${y}`}
              x={offset + x * (cell + gap)}
              y={offset + y * (cell + gap)}
              width={cell}
              height={cell}
              rx={0.3}
              fill="currentColor"
              opacity={
                // Varying opacity for defrag feel
                (x + y) % 3 === 0 ? 1 : (x + y) % 3 === 1 ? 0.7 : 0.45
              }
            />
          ) : null,
        ),
      )}
    </svg>
  );
}

export const icons = {
  brain: IconBrain,
  database: IconDatabase,
  clock: IconClock,
  filter: IconFilter,
  search: IconSearch,
  grid: IconGrid,
  list: IconList,
  chevronLeft: IconChevronLeft,
  chevronRight: IconChevronRight,
  chevronDown: IconChevronDown,
  chevronUp: IconChevronUp,
  settings: IconSettings,
  refresh: IconRefresh,
  activity: IconActivity,
  terminal: IconTerminal,
  code: IconCode,
  message: IconMessage,
  play: IconPlay,
  check: IconCheck,
  x: IconX,
  expand: IconExpand,
  zap: IconZap,
  export: IconExport,
  defragLogo: IconDefragLogo,
} as const;

export type IconName = keyof typeof icons;

export function Icon({ name, ...props }: IconProps & { name: IconName }) {
  const Comp = icons[name];
  return <Comp {...props} />;
}
