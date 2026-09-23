import { faCircleNotch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";

export default function LoadingPage() {
   const { t } = useLingui();

   return (
      <BaseLayout>
         <LayoutMain title={t`Laden…`}>
            <div className="flex w-full flex-1 items-center justify-center">
               <div role="status" className="flex items-center gap-2 text-gray-700 text-lg">
                  <FontAwesomeIcon icon={faCircleNotch} className="animate-spin motion-reduce:animate-none" />
                  <Trans>Laden…</Trans>
               </div>
            </div>
         </LayoutMain>
      </BaseLayout>
   );
}
