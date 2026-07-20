import type { ReactNode } from 'react'
import type { IconDefinition } from '@fortawesome/fontawesome-svg-core'
import { faFolder } from '@fortawesome/free-regular-svg-icons'
import { faFile } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import type { ElectionDocument } from '../../api/types'

type ReportFile = ElectionDocument & {
    icon: ReactNode
}

type Props = {
    title: string
    subtitle?: string
    description: string
    documents: ElectionDocument[] | undefined
}

const FILE_TYPE_MAPPINGS: Record<
    string,
    { name: string; fileType: string; description: string; icon: IconDefinition }
> = {
    EML510b: {
        name: 'EML_NL tellingbestand 510b',
        fileType: 'xml',
        icon: faFolder,
        description:
            'Output van de optelsoftware, bevat de resultaten van alle stembureaus en de optelling van de hele gemeente.',
    },
}

function formatFileSize(size: number | string): string {
    const bytes = typeof size === 'string' ? Number(size) : size

    if (!Number.isFinite(bytes) || bytes < 0) {
        return String(size)
    }

    if (bytes < 1024) {
        return `${bytes} B`
    }

    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`
    }

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function toReportFiles(documents: ElectionDocument[] | undefined): ReportFile[] {
    return (documents ?? []).map((document) => ({
        ...document,
        icon: (
            <FontAwesomeIcon
                icon={FILE_TYPE_MAPPINGS[document.file_type]?.icon ?? faFile}
            />
        ),
    }))
}

export default function ReportsWithResults({ title, subtitle, description, documents }: Props) {
    const files = toReportFiles(documents)

    if (files.length === 0) {
        return null
    }

    return (
        <div className={'results-reports'}>
            <h3 className={'results-reports-title mb-2'}>{title}</h3>
            {subtitle && <h5 className={'results-reports-subtitle mb-3'}>{subtitle}</h5>}
            <p className={'results-reports-description mb-3'}>{description}</p>
            <div className={'results-reports-files'}>
                {files.map((file) => (
                    <div key={file.file_type} className={'results-reports-item'}>
                        <div className={'results-reports-icon'}>
                            {file.icon}
                        </div>
                        <div className={'results-reports-content'}>
                            <a
                                href={file.url}
                                className={'results-reports-content-title'}
                                download
                            >
                                <span className={'bold'}>
                                    {FILE_TYPE_MAPPINGS[file.file_type]?.name ?? file.name}
                                </span> ({FILE_TYPE_MAPPINGS[file.file_type]?.fileType ?? file.type}, {formatFileSize(file.size)})

                            </a>
                            <span className="results-reports-description-text">
                                {FILE_TYPE_MAPPINGS[file.file_type]?.description ?? file.description}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
