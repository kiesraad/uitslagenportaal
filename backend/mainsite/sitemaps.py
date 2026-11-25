from collections import defaultdict

from django.contrib.sitemaps import Sitemap

from election.models import ElectionConfig, VoteCount
from mainsite.models import RegionCategory
from region.models import Region, hsb_kieskringen


class FrontendSitemap(Sitemap):
    """Lists frontend paths; expired elections are left out by `ElectionConfig.objects`."""

    protocol = "https"

    def location(self, item):
        return item


class ElectionSitemap(FrontendSitemap):
    def items(self):
        configs = list(ElectionConfig.objects.order_by("-date"))
        paths = ["/"]
        for config in configs:
            # With a single election the homepage shows the timeline instead.
            if len(configs) > 1:
                paths.append(f"/{config.slug}/van-stem-tot-uitslag")
            paths.append(f"/{config.slug}/gsb")
            if config.has_hsb:
                paths.append(f"/{config.slug}/hsb")
            paths.append(f"/{config.slug}/csb")
        return paths


def _region_bases():
    """Path and region of each CSB, HSB and municipality, linked the way the frontend's region lists link them."""
    for config in ElectionConfig.objects.order_by("-date"):
        regions = Region.objects.filter(election__election_config=config).select_related("csb").order_by("slug")
        for region in regions.filter(region_category=config.csb_type):
            yield f"/{config.slug}/csb/{region.slug}", region
        for region in hsb_kieskringen(regions):
            yield f"/{config.slug}/hsb/{region.slug}", region
        for region in regions.filter(region_category=RegionCategory.GEMEENTE):
            csb = f"/csb/{region.csb.slug}" if region.csb else ""
            yield f"/{config.slug}/gsb/{region.slug}{csb}", region


class RegionSitemap(FrontendSitemap):
    def items(self):
        return [path for base, _ in _region_bases() for path in (base, f"{base}/resultaten")]


class PartySitemap(FrontendSitemap):
    """The results of each party with votes in a region or in a municipality below it; others are a 404 there."""

    def items(self):
        # A GR gemeente is listed both as CSB and as municipality.
        bases = defaultdict(list)
        for base, region in _region_bases():
            bases[region.id].append(base)
        votes = VoteCount.objects.filter(region__in=bases)
        party_slugs = set()
        for region_field in ("region_id", "region__parent_id", "region__csb_id"):
            party_slugs.update(votes.values_list(region_field, "party__slug").distinct())
        return [
            f"{base}/resultaten/{slug}"
            for region_id, slug in sorted(party_slugs, key=lambda pair: (pair[0] or 0, pair[1]))
            for base in bases.get(region_id, [])
        ]


sitemaps = {"verkiezingen": ElectionSitemap, "regios": RegionSitemap, "partijen": PartySitemap}
