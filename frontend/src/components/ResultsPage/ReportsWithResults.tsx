import type { ElectionDocument } from "@/api/types.ts";
import ElectionFileEntry from "@/components/ElectionFileEntry.tsx";

type Props = {
   title: string;
   subtitle?: string;
   description: string;
   documents: ElectionDocument[] | undefined;
};

export default function ReportsWithResults({ title, subtitle, description, documents }: Props) {
   if (!documents || documents.length === 0) {
      return null;
   }

   return (
      <div>
         <h3 className="mb-2">{title}</h3>
         {subtitle && <p className="mb-3">{subtitle}</p>}
         <p className="mb-3">{description}</p>
         <div>
            {documents.map((file) => (
               <ElectionFileEntry key={file.url} file={file} />
            ))}
         </div>
      </div>
   );
}
