import { type ChangeEvent, type KeyboardEvent, type ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import { faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

export type SearchListOption = {
  id: string
  label: string
  searchText?: string
  content?: ReactNode
}

type Props = {
  inputId: string
  label: string
  options: SearchListOption[]
  placeholder: string
  onSelect: (option: SearchListOption) => void
  submitBehavior?: 'exact-match' | 'first-match'
  maxSuggestions?: number
  children?: ReactNode
}

export default function SearchListSearch({
  inputId,
  label,
  options,
  placeholder,
  onSelect,
  submitBehavior = 'exact-match',
  maxSuggestions = 8,
  children,
}: Props) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(-1)
  const [open, setOpen] = useState(false)
  const listRef = useRef<HTMLUListElement>(null)
  const suggestionsId = `${inputId}-suggestions`

  const suggestions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    if (normalizedQuery.length === 0) {
      return []
    }

    return options
      .filter((option) => {
        const searchable = `${option.label} ${option.searchText ?? ''}`.toLowerCase()

        return searchable.includes(normalizedQuery)
      })
      .slice(0, maxSuggestions)
  }, [maxSuggestions, options, query])
  const isOpen = open && query.trim().length > 0 && suggestions.length > 0

  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) {
      return
    }

    const item = listRef.current.children[activeIndex] as HTMLElement
    item?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  function selectOption(option: SearchListOption) {
    setQuery(option.label)
    setOpen(false)
    onSelect(option)
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value)
    setActiveIndex(-1)
    setOpen(true)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!isOpen) {
      return
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((index) => Math.min(index + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  function handleSubmit() {
    const normalizedQuery = query.trim().toLowerCase()
    const exact = options.find((option) => option.label.toLowerCase() === normalizedQuery)
    const option =
      (activeIndex >= 0 ? suggestions[activeIndex] : undefined) ??
      exact ??
      (submitBehavior === 'first-match' ? suggestions[0] : undefined)

    if (option) {
      selectOption(option)
    }
  }

  return (
    <>
      <label className="search-label" htmlFor={inputId}>
        {label}
      </label>
      <div className="search-row">
        <div className="search-input-wrapper">
          <input
            id={inputId}
            className="search-input"
            type="text"
            placeholder={placeholder}
            autoComplete="off"
            value={query}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            onFocus={() => suggestions.length > 0 && setOpen(true)}
            aria-autocomplete="list"
            aria-expanded={isOpen}
            aria-controls={suggestionsId}
            aria-activedescendant={activeIndex >= 0 ? `${suggestionsId}-${activeIndex}` : undefined}
          />
          {isOpen && (
            <ul
              id={suggestionsId}
              ref={listRef}
              role="listbox"
              className="search-suggestions"
            >
              {suggestions.map((option, index) => (
                <li
                  key={option.id}
                  id={`${suggestionsId}-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={`search-suggestion-item${index === activeIndex ? ' active' : ''}`}
                  onMouseDown={() => selectOption(option)}
                  onMouseEnter={() => setActiveIndex(index)}
                >
                  {option.content ?? option.label}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          className="search-btn"
          type="button"
          aria-label="Zoeken"
          onClick={handleSubmit}
        >
          <FontAwesomeIcon icon={faMagnifyingGlass} style={{ }} />
        </button>
        {children}
      </div>
    </>
  )
}
