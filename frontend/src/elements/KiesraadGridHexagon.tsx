export default function KiesraadGridHexagon({ className }: { className?: string }) {
   return (
      <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true" className={className}>
         <polygon points="4,0 7.46,2 7.46,6 4,8 0.54,6 0.54,2" fill="currentColor" />
      </svg>
   );
}
