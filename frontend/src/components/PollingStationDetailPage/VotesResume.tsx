type Props = {
    votes: {
        name: string;
        count: number;
        bold?: boolean;
    }[]
}
export default function VotesResume({ votes }: Props) {

    return (
        <div className={'admitted-voters-box'}>
            {votes.map((vote) => (
                <div key={vote.name} className={`admitted-voters-item ${vote.bold ? 'bold' : ''}`}>
                    <span>{vote.name}</span>
                    <span>{vote.count}</span>
                </div>
            ))}
        </div>
    );
}
