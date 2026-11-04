// Minimal inline SVG icons. Stroke-based and inherit `currentColor`, so they theme automatically.
const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

export const BagIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M5 8h14l-1.2 11.2a2 2 0 0 1-2 1.8H8.2a2 2 0 0 1-2-1.8L5 8Z" />
    <path d="M9 8V7a3 3 0 0 1 6 0v1" />
  </svg>
)

export const SparkIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />
    <path d="M19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15Z" />
  </svg>
)

export const ArrowUpIcon = (props) => (
  <svg {...base} strokeWidth={2.2} {...props}>
    <path d="M12 19V5" />
    <path d="m5 12 7-7 7 7" />
  </svg>
)

export const PlusIcon = (props) => (
  <svg {...base} strokeWidth={2.2} {...props}>
    <path d="M12 5v14M5 12h14" />
  </svg>
)

export const CheckIcon = (props) => (
  <svg {...base} strokeWidth={2.4} {...props}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </svg>
)

export const XIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M6 6l12 12M18 6 6 18" />
  </svg>
)

export const EditIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" />
  </svg>
)

export const LockIcon = (props) => (
  <svg {...base} {...props}>
    <rect x="5" y="11" width="14" height="10" rx="2" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
  </svg>
)

export const StarIcon = (props) => (
  <svg {...base} fill="currentColor" stroke="none" {...props}>
    <path d="M12 2.8l2.8 5.8 6.3.9-4.6 4.4 1.1 6.3L12 17.2l-5.6 3 1.1-6.3L2.9 9.5l6.3-.9L12 2.8Z" />
  </svg>
)
