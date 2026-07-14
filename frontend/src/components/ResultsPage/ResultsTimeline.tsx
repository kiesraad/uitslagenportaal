import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Timeline from "../Timeline";
import type { Step } from "../Timeline";
import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";

type Props = {
    title: string;
    description?: string;
    steps: Step[]
}
export default function ResultsTimeline({ title, description, steps }: Props ) {
    return (
        <div>
            <h2 className="result-how-title">{title}</h2>
            {description ? <p className={'mb-4'}>{description}</p> : null}
            <p className="result-order-hint">
                <span><FontAwesomeIcon icon={faArrowUp} color="Black"/><FontAwesomeIcon icon={faArrowDown} color="Grey"/></span>
                <a href="#">Laatste stap bovenaan</a>
            </p>

            {/* Timeline */}
            <Timeline
                steps={steps}
            />
        </div>
    )
}