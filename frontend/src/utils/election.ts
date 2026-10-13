import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import type { ElectionCategory } from "../api/types";

export type SingleCsbTab = {
   label: MessageDescriptor;
   regionSlug: string;
};

// TK and EP always have one CSB; the tab uses that name and skips the list.
const SINGLE_CSB_TABS: Partial<Record<ElectionCategory, SingleCsbTab>> = (() => ({
   TK: { label: msg`Nederland`, regionSlug: "nederland" },
   EP: { label: msg`Europees Parlement`, regionSlug: "nederland" },
}))();

export function getSingleCsbTab(category: ElectionCategory): SingleCsbTab | undefined {
   return SINGLE_CSB_TABS[category];
}
