import { useMemo, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Timeline from "../Timeline";
import type { TimelineEntry } from "../Timeline";
import type { TimelineVariant } from "@/api/types.ts";
import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";

type SortDirection = 'desc' | 'asc'

const VARIANT_DESCRIPTIONS: Record<TimelineVariant, string> = {
    CSO: 'Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.',
    DSO: 'Het stembureau doet een uitgebreide telling op het stembureau. Het gemeentelijk stembureau telt de volgende dag de uitkomsten bij elkaar op. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.',
    DEFAULT: '',
}

type Props = {
    description?: string;
    variant?: TimelineVariant;
    entries: TimelineEntry[]
}
export default function ResultsTimeline({ description, variant, entries }: Props ) {
    // 'desc' shows the most recent entry on top ("Laatste stap bovenaan").
    const [direction, setDirection] = useState<SortDirection>('desc')

    const resolvedDescription = description ?? (variant ? VARIANT_DESCRIPTIONS[variant] : '')
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
            {resolvedDescription ? <p className={'mb-4'}>{resolvedDescription}</p> : null}
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