/**
 * The mid-sentence form of a standalone label: "Gemeente" → "gemeente".
 *
 * Only correct in languages that lowercase common nouns mid-sentence, which
 * holds for the locales in `lingui.config.ts` (Dutch and English). A language
 * that capitalises nouns everywhere would need the inline form to come from the
 * catalogue again.
 */
export function lowercaseFirst(label: string): string {
   return label.charAt(0).toLocaleLowerCase() + label.slice(1);
}

/** The sentence-initial form of a label: "de gemeente Utrecht" → "De gemeente Utrecht". */
export function uppercaseFirst(label: string): string {
   return label.charAt(0).toLocaleUpperCase() + label.slice(1);
}
