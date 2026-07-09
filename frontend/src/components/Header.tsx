import { Link } from 'react-router-dom'

export function Header() {
  return (
    <header className="header">
      <div className="header-inner">
        <Link to="/" className="header-logo">
          <img src="/kiesraad_logo.png" alt="Kiesraad" className="header-logo-img" />
        </Link>
      </div>
    </header>
  )
}
