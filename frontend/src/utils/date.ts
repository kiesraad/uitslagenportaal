import { plural, t } from "@lingui/core/macro";

const MS_PER_MINUTE = 60 * 1000;
const MS_PER_HOUR = 60 * MS_PER_MINUTE;
const MS_PER_DAY = 24 * MS_PER_HOUR;

/**
 * Remaining time until an ISO deadline, using days (>= 24h), hours (>= 1h),
 * or minutes. Returns null when the deadline has passed or the date is invalid.
 */
export function getRemainingReportTime(
   isoDeadline: string,
   now = new Date(),
): {
   value: number;
   unit: "day" | "hour" | "minute";
} | null {
   const deadline = new Date(isoDeadline);
   if (Number.isNaN(deadline.getTime())) {
      return null;
   }

   const remainingMs = deadline.getTime() - now.getTime();
   if (remainingMs <= 0) {
      return null;
   }

   if (remainingMs >= MS_PER_DAY) {
      return { value: Math.floor(remainingMs / MS_PER_DAY), unit: "day" };
   }
   if (remainingMs >= MS_PER_HOUR) {
      return { value: Math.floor(remainingMs / MS_PER_HOUR), unit: "hour" };
   }
   return { value: Math.max(1, Math.ceil(remainingMs / MS_PER_MINUTE)), unit: "minute" };
}

/**
 * The heading above the issue report form, counting down to the deadline.
 *
 * The plural forms live in the message catalogue rather than in this function,
 * so a translator decides how many forms their language needs.
 */
export function formatIssueReportDeadlineHeading(isoDeadline: string, now = new Date()): string {
   const remaining = getRemainingReportTime(isoDeadline, now);
   if (!remaining) {
      return t`U kunt geen fout meer melden`;
   }

   switch (remaining.unit) {
      case "day":
         return plural(remaining.value, {
            one: "U heeft nog # dag om een melding te maken",
            other: "U heeft nog # dagen om een melding te maken",
         });
      case "hour":
         return plural(remaining.value, {
            one: "U heeft nog # uur om een melding te maken",
            other: "U heeft nog # uur om een melding te maken",
         });
      case "minute":
         return plural(remaining.value, {
            one: "U heeft nog # minuut om een melding te maken",
            other: "U heeft nog # minuten om een melding te maken",
         });
   }
}
