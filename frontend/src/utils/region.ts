  // Helper mapping from csb_type to singular and plural camelcase versions
  const csbTypeMapping: Record<
    string,
    { singular: string; plural: string }
  > = {
    STAAT: { singular: "Staat", plural: "Staten" },
    WATERSCHAP: { singular: "Waterschap", plural: "Waterschappen" },
    KIESKRING: { singular: "Kieskring", plural: "Kieskringen" },
    GEMEENTE: { singular: "Gemeente", plural: "Gemeenten" },
    PROVINCIE: { singular: "Provincie", plural: "Provincies" },
    STEMBUREAU: { singular: "Stembureau", plural: "Stembureaus" },
  }

  export function getRegionLabel(
    csbType?: string,
    plural = false
  ): string {
    if (!csbType) return ""
    const mapping = csbTypeMapping[csbType]
    if (!mapping) return ""
    return plural ? mapping.plural : mapping.singular
  }