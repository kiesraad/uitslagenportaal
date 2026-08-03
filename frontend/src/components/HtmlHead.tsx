interface HtmlHeadProps {
  title?: string
  description?: string
}

export default function HtmlHead({title, description}: HtmlHeadProps) {
  const pageTitle = [title || "", "Kiesraad"].join(" - ")
  return (
    <>
      <title>{pageTitle}</title>
      <meta name="description" content={description || title}/>
    </>
  )
}
