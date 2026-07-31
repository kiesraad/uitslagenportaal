import { useMemo, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Timeline from "../Timeline";
import type { TimelineEntry } from "../Timeline";
import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";

type SortDirection = 'desc' | 'asc'

type Props = {
    description?: string;
    entries: TimelineEntry[]
}
export default function ResultsTimeline({ description, entries }: Props ) {
    // 'desc' shows the most recent entry on top ("Laatste stap bovenaan").
    const [direction, setDirection] = useState<SortDirection>('desc')

    const sortedEntries = useMemo(() => {
        const factor = direction === 'desc' ? -1 : 1
        return [...entries].sort(
            (a, b) => factor * (new Date(a.date).getTime() - new Date(b.date).getTime()),
        )
    }, [entries, direction])

    const toggleDirection = (event: React.MouseEvent<HTMLAnchorElement>) => {
        event.preventDefault()
        setDirection((current) => (current === 'desc' ? 'asc' : 'desc'))
    }

    return (
        <div id='results-timeline'>
            <h2 className="result-how-title">Hoe zijn de resultaten tot stand gekomen?</h2>
            {description ? <p className={'mb-4'}>{description}</p> : null}
            <p className="result-order-hint">
                <span>
                    <FontAwesomeIcon icon={faArrowUp} color={direction === 'desc' ? 'Black' : 'Grey'} />
                    <FontAwesomeIcon icon={faArrowDown} color={direction === 'asc' ? 'Black' : 'Grey'} />
                </span>
                <a href="#" onClick={toggleDirection}>
                    {direction === 'desc' ? 'Laatste stap bovenaan' : 'Eerste stap bovenaan'}
                </a>
            </p>

            {/* Timeline */}
            <Timeline
                entries={sortedEntries}
            />
        </div>
    )
}