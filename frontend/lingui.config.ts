import { defineConfig } from "@lingui/cli";
import { formatter } from "@lingui/format-po";

export default defineConfig({
   // Source files are written in Dutch, so the `nl` catalogue is generated from
   // the source itself and never needs translating by hand.
   sourceLocale: "nl",
   locales: ["nl", "en"],
   // An English message without a translation renders the Dutch source rather
   // than a generated message id.
   fallbackLocales: { en: "nl" },
   catalogs: [
      {
         path: "<rootDir>/src/locales/{locale}/messages",
         include: ["src"],
         exclude: ["**/*.test.*", "**/node_modules/**"],
      },
   ],
   // `lineNumbers: false` keeps catalogue diffs readable: line-number comments
   // otherwise churn on nearly every source edit.
   format: formatter({ lineNumbers: false }),
});
