import type { Candidate } from '../api/types'

export function formatCandidateName(candidate: Candidate | null): string {
  const surname = [candidate?.name_prefix, candidate?.last_name].filter(Boolean).join(' ')

  if (candidate?.first_name) {
    const initials = candidate.initials || candidate.first_name.charAt(0)
    return `${surname}, ${initials} (${candidate.first_name})`
  }

  if (candidate?.initials) {
    return `${surname}, ${candidate.initials}`
  }

  return surname
}
