import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";

/** Tells screen reader users that a `target="_blank"` link opens a new window; sighted users get the icon. */
export function NewWindowHint() {
   return (
      <span className="sr-only">
         {" "}
         <Trans>(opent in nieuw venster)</Trans>
      </span>
   );
}

/** `newWindowHint={false}` for when the icon sits on something that is not a new-window link, like a disabled button. */
export function ExternalLinkIcon({ newWindowHint = true }: { newWindowHint?: boolean }) {
   return (
      <>
         <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
         {newWindowHint && <NewWindowHint />}
      </>
   );
}
