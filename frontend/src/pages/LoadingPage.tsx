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
            <div className="flex items-center justify-center w-full flex-1">
               <div className="flex items-center text-lg gap-2 text-gray-700">
                  <FontAwesomeIcon icon={faCircleNotch} className="animate-spin" />
                  <Trans>Laden…</Trans>
               </div>
            </div>
         </LayoutMain>
      </BaseLayout>
   );
}
