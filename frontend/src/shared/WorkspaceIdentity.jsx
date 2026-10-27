import React, { useId } from "react";
import {
  LayoutDashboard,
  Clapperboard,
  Bubbles,
  Braces,
  Blocks,
  Smartphone,
  Package,
  BookOpen,
  Sprout,
  Terminal,
  Hotel,
  Sparkles,
  NotebookPen,
  Fingerprint,
  Files,
  Image,
  Binary,
  HeartHandshake,
  Cable,
  Users,
  Workflow,
} from "lucide-react";

const icons = {
  home: LayoutDashboard,
  emote_ui_automation: Clapperboard,
  circle_stats: Bubbles,
  api_workspace: Braces,
  jenkins: Blocks,
  online_preview: Smartphone,
  test_packages: Package,
  learning: BookOpen,
  self_study: Sprout,
  command_library: Terminal,
  restful_booker: Hotel,
  effects: Sparkles,
  work_journal: NotebookPen,
  data_generator: Fingerprint,
  files: Files,
  images: Image,
  json_tools: Braces,
  codec: Binary,
  family_oa_web: HeartHandshake,
  integrations: Cable,
  users: Users,
  oa_management: Workflow,
};
export function WorkspaceIcon({ name, size = 19, ...props }) {
  const Icon = icons[name] || Sparkles;
  return <Icon size={size} strokeWidth={1.65} aria-hidden="true" {...props} />;
}
export function BrandMark({ className = "" }) {
  return (
    <span className={`atelier-mark ${className}`} aria-hidden="true">
      <svg viewBox="0 0 40 40" fill="none">
        <path
          d="M20 4C21.5 14.5 25.5 18.5 36 20C25.5 21.5 21.5 25.5 20 36C18.5 25.5 14.5 21.5 4 20C14.5 18.5 18.5 14.5 20 4Z"
          fill="currentColor"
        />
        <circle cx="31.5" cy="8.5" r="2.5" fill="currentColor" />
      </svg>
    </span>
  );
}
export function OrbitArtwork({ className = "" }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg
      className={`atelier-orbit ${className}`}
      viewBox="0 0 440 360"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id={`${id}-orb`} cx=".33" cy=".24" r=".85">
          <stop stopColor="#fffdf8" />
          <stop offset=".46" stopColor="#e6deef" />
          <stop offset="1" stopColor="#a999cf" />
        </radialGradient>
        <linearGradient
          id={`${id}-ring`}
          x1="80"
          y1="60"
          x2="350"
          y2="300"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#af9fca" />
          <stop offset="1" stopColor="#efe9dc" />
        </linearGradient>
      </defs>
      <path d="M85 266H367M85 301H367" stroke="#dcd4df" strokeDasharray="2 7" />
      <ellipse
        cx="220"
        cy="174"
        rx="148"
        ry="62"
        transform="rotate(-34 220 174)"
        stroke={`url(#${id}-ring)`}
        strokeWidth="1.2"
      />
      <ellipse
        cx="220"
        cy="174"
        rx="133"
        ry="99"
        transform="rotate(42 220 174)"
        stroke="#d6cbdf"
      />
      <circle cx="220" cy="174" r="79" fill={`url(#${id}-orb)`} />
      <path
        d="M91 247C118 273 202 248 282 194C362 140 393 81 364 64"
        stroke="#b9a8cd"
        strokeWidth="1.5"
      />
      <circle cx="105" cy="238" r="13" fill="#f0c8a8" />
      <circle cx="339" cy="101" r="6" fill="#7d6b9d" />
      <path d="M324 228V250M313 239H335" stroke="#8c789f" strokeWidth="1.5" />
      <circle cx="114" cy="100" r="3" fill="#b5c8ba" />
      <path
        d="M206 156C212 166 225 170 238 164"
        stroke="white"
        strokeOpacity=".7"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <text
        x="91"
        y="324"
        fill="#7a7182"
        fontFamily="monospace"
        fontSize="9"
        letterSpacing="3"
      >
        SMALL STEPS. MEANINGFUL WORK.
      </text>
    </svg>
  );
}
