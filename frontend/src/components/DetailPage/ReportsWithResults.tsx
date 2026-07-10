import type { ReactNode } from 'react'

type Props = {
    title: string;
    subtitle?: string;
    description: string;
    files: {
        name: string;
        url: string;
        type: string;
        size: string;
        description: string;
        icon: ReactNode;
    }[]
}
export default function ReportsWithResults({ title, subtitle, description, files }: Props) {
    return (
        <div className={'results-reports'}>
            <h3 className={'results-reports-title mb-2'}>{title}</h3>
            {subtitle && <h5 className={'results-reports-subtitle mb-3'}>{subtitle}</h5>}
            <p className={'results-reports-description mb-3'}>{description}</p>
            <div className={'results-reports-files'}>
                {files.map((file) => (
                    <div key={file.name} className={'results-reports-item'}>
                        <div className={'results-reports-icon'}>
                            {file.icon}
                        </div>
                        <div className={'results-reports-content'}>
                            <span className={'results-reports-content-title'}><span className={'bold'}>{file.name}</span> ({file.type}, {file.size})</span>
                            <span>{file.description}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
