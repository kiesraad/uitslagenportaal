import type { I18n, MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react";
import { useMemo } from "react";
import type { TimelineDate } from "@/api/types.ts";
import { type Locale, resolveLocale } from "../i18n";

/**
 * Election times are always Dutch local time, whatever language the interface
 * is in, so the zone is fixed while the formatting follows the active locale.
 */
const ELECTION_TIME_ZONE = "Europe/Amsterdam";

/**
 * Regional conventions to format with, per interface language.
 *
 * The message catalogues are keyed by language (`en`), but bare `en` formats
 * American-style — "December 8 at 09:00 PM" and `1,234` on a 12-hour clock.
 * This project writes British English, so dates and times follow `en-GB`:
 * "8 December at 21:00".
 */
const INTL_LOCALES: Record<Locale, string> = {
   nl: "nl-NL",
   en: "en-GB",
};

const DAY_MONTH_FORMAT: Intl.DateTimeFormatOptions = {
   day: "numeric",
   month: "long",
   timeZone: ELECTION_TIME_ZONE,
};

const FULL_DATE_FORMAT: Intl.DateTimeFormatOptions = {
   day: "numeric",
   month: "long",
   year: "numeric",
   timeZone: ELECTION_TIME_ZONE,
};

const TIME_FORMAT: Intl.DateTimeFormatOptions = {
   hour: "2-digit",
   minute: "2-digit",
   timeZone: ELECTION_TIME_ZONE,
};

// Intl offers no way to pick the word between date and time, and its own choice
// differs between ICU versions, so the two are joined here instead.
const DATE_TIME_DELIMITERS = {
   dash: "-",
   at: msg({ message: "om", comment: "Between a date and a time: 8 december om 21:00" }),
   after: msg({ message: "na", comment: "Between a date and a time: 8 december na 21:00" }),
   until: msg({ message: "tot", comment: "Between a date and a time: 8 december tot 21:00" }),
   none: "",
} satisfies Record<string, string | MessageDescriptor>;

export type DateTimeDelimiter = keyof typeof DATE_TIME_DELIMITERS;

export type DateTimeOptions = {
   delimiter?: DateTimeDelimiter;
   withYear?: boolean;
   withTime?: boolean;
};

// Building an Intl formatter is expensive relative to using one, and the vote
// tables format hundreds of cells per render, so instances are cached per
// locale-and-options rather than constructed at each call site.
const numberFormatters = new Map<string, Intl.NumberFormat>();
const dateFormatters = new Map<string, Intl.DateTimeFormat>();
const collators = new Map<string, Intl.Collator>();

function numberFormatter(locale: Locale, options?: Intl.NumberFormatOptions): Intl.NumberFormat {
   const key = `${locale}:${JSON.stringify(options ?? {})}`;
   let formatter = numberFormatters.get(key);
   if (!formatter) {
      formatter = new Intl.NumberFormat(INTL_LOCALES[locale], options);
      numberFormatters.set(key, formatter);
   }
   return formatter;
}

function dateFormatter(locale: Locale, options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
   const key = `${locale}:${JSON.stringify(options)}`;
   let formatter = dateFormatters.get(key);
   if (!formatter) {
      formatter = new Intl.DateTimeFormat(INTL_LOCALES[locale], options);
      dateFormatters.set(key, formatter);
   }
   return formatter;
}

export function getCollator(locale: Locale): Intl.Collator {
   let collator = collators.get(locale);
   if (!collator) {
      collator = new Intl.Collator(INTL_LOCALES[locale]);
      collators.set(locale, collator);
   }
   return collator;
}

export function formatNumber(locale: Locale, value: number, options?: Intl.NumberFormatOptions): string {
   return numberFormatter(locale, options).format(value);
}

/**
 * Formats an ISO date string with time, "10 december 2025 - 12:17" by default, or
 * e.g. "8 december om 21:00" with `options`. Returns the input unchanged if it cannot be parsed.
 */
export function formatDate(
   i18n: I18n,
   locale: Locale,
   isoDate: string,
   { delimiter = "dash", withYear = true, withTime = true }: DateTimeOptions = {},
): string {
   const date = new Date(isoDate);
   if (Number.isNaN(date.getTime())) {
      return isoDate;
   }
   const datePart = dateFormatter(locale, withYear ? FULL_DATE_FORMAT : DAY_MONTH_FORMAT).format(date);
   const timePart = dateFormatter(locale, TIME_FORMAT).format(date);
   const separator = DATE_TIME_DELIMITERS[delimiter];
   const separatorText = typeof separator === "string" ? separator : i18n._(separator);
   if (!withTime) {
      return datePart;
   }
   return [datePart, separatorText, timePart].filter(Boolean).join(" ");
}

export function formatTimelineDate(i18n: I18n, locale: Locale, date: TimelineDate): string {
   switch (date.qualifier) {
      case "all_day":
         return formatDate(i18n, locale, date.date, { withYear: false, withTime: false });
      case "from":
         return formatDate(i18n, locale, date.date, { delimiter: "after", withYear: false });
      case "until":
         return formatDate(i18n, locale, date.date, { delimiter: "until", withYear: false });
      case "expected":
         return `${i18n._(msg`Verwacht:`)} ${formatDate(i18n, locale, date.date, { delimiter: "at", withYear: false })}`;
   }
}

// en-CA writes dates as YYYY-MM-DD, so two days compare as strings.
const electionDayFormatter = new Intl.DateTimeFormat("en-CA", {
   year: "numeric",
   month: "2-digit",
   day: "2-digit",
   timeZone: ELECTION_TIME_ZONE,
});

/** The calendar day a moment falls on in Dutch local time, as "2026-03-20". */
export function electionDay(date: Date): string {
   return electionDayFormatter.format(date);
}

/** Formats an election day without a time, e.g. "20 maart 2026". */
export function formatElectionDate(locale: Locale, isoDate: string): string {
   const date = new Date(isoDate);
   if (Number.isNaN(date.getTime())) {
      return isoDate;
   }
   return dateFormatter(locale, FULL_DATE_FORMAT).format(date);
}

const FILE_SIZE_UNITS = ["B", "KB", "MB", "GB"] as const;

/**
 * Formats a byte count with a locale-appropriate decimal separator, so file
 * sizes match the vote totals shown alongside them.
 */
export function formatFileSize(locale: Locale, bytes: number): string {
   let size = bytes;
   let unitIndex = 0;
   while (size >= 1024 && unitIndex < FILE_SIZE_UNITS.length - 1) {
      size /= 1024;
      unitIndex += 1;
   }
   const fractionDigits = unitIndex === 0 ? 0 : 1;
   const formatted = formatNumber(locale, size, {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
   });
   return `${formatted} ${FILE_SIZE_UNITS[unitIndex]}`;
}

/**
 * Formatters bound to the active locale.
 *
 * Note the `i18n.locale` dependency: the `i18n` object itself is a stable
 * reference that does not change when the language does, so memoising on it
 * would silently keep the old locale's formatting forever. Is added as useMemo
 * dependency to silence Biome.
 */
export function useFormatters() {
   const { i18n } = useLingui();
   const locale = resolveLocale(i18n.locale);

   return useMemo(
      () => ({
         locale,
         formatNumber: (value: number, options?: Intl.NumberFormatOptions) => formatNumber(locale, value, options),
         formatDate: (isoDate: string, options?: DateTimeOptions) => formatDate(i18n, locale, isoDate, options),
         formatElectionDate: (isoDate: string) => formatElectionDate(locale, isoDate),
         formatTimelineDate: (date: TimelineDate) => formatTimelineDate(i18n, locale, date),
         formatFileSize: (bytes: number) => formatFileSize(locale, bytes),
         collator: getCollator(locale),
      }),
      [locale, i18n],
   );
}
