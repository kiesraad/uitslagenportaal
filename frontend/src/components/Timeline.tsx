import { faCheck, faFile } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import ReactMarkdown from 'react-markdown';

type State = 'pending' | 'in-progress' | 'done'
export interface Step {
    state: State
    title: string
    date: string
    body: string;
    link?: string
    files?: {
        name: string;
        url: string;
        type: string;
        size: string;
        description: string;
    }[]
}
type Props = {
    steps: Step[]
}
export default function Timeline({ steps }: Props) {
    return (
        <div className="timeline">
            {steps.map((step, i) => (
                <div key={step.title} className={`timeline-item`}>
                    <div className={`timeline-line ${step.state} ${step.state === 'done' ? 'border-solid' : 'border-dashed'} ${steps.length === i + 1 ? 'last' : ''}`}></div>
                    <div className={'tl-marker-container'}>
                        <div className={`tl-marker ${step.state}`}>
                            <div className={`${step.state}-layer-1`}></div>
                            {step.state === 'done' ? (
                                <FontAwesomeIcon icon={faCheck} />
                            ) : null}
                        </div>
                    </div>
                    <div className="tl-body">
                        <div className="tl-title">{step.title}</div>
                        <div className="tl-date">{step.date}</div>
                        <div className="tl-desc">
                            <ReactMarkdown>{step.body}</ReactMarkdown>
                        </div>
                        {step.link && (
                            <div className="tl-link">
                                <a href="#">{step.link}</a>
                            </div>
                        )}
                        {step.files ? (
                            <div className="tl-files mt-3">
                                {step.files.map((file, i) => (
                                    <a href={file.url} key={i} className={'tl-files-item'}>
                                        <FontAwesomeIcon icon={faFile} />
                                        <div className={'tl-files-content'}>
                                            <span className={'tl-files-content-title mb-1'}><span className={'bold'}>{file.name}</span> ({file.type}, {file.size})</span>
                                            <span className={'tl-files-content-desc'}>{file.description}</span>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        ) : null}
                    </div>
                </div>
            ))}
        </div>
    )
}