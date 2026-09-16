from django.db.models import TextChoices


class EmlType(TextChoices):
    """
    Enum of EML types, with their labels.
    """

    # Labels should not be changed as they're used to determine the EML file names.
    # Changing them will result in different file names when importing the same data.
    EML_110a = "110a", "Verkiezingsdefinitie"
    EML_110b = "110b", "Stembureaus"
    EML_230b = "230b", "Kandidatenlijsten"
    EML_510a = "510a", "Telling SB"
    EML_510b = "510b", "Telling GSB"
    EML_510c = "510c", "Totaaltelling HSB"
    EML_510d = "510d", "Totaaltelling CSB"
    EML_520 = "520", "Resultaat"


class ReportingLevel(TextChoices):
    GSB = "gsb"
    HSB = "hsb"
    CSB = "csb"


# The reporting body, not the region's geography, decides which telling to show.
# A GR gemeente is GSB on /gsb/ and CSB on /csb/; same row, different file.
EML_TYPE_BY_REPORTING_LEVEL = {
    ReportingLevel.GSB: EmlType.EML_510b,
    ReportingLevel.HSB: EmlType.EML_510c,
    ReportingLevel.CSB: EmlType.EML_510d,
}
