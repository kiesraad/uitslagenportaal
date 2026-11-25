from django.contrib.sitemaps import Sitemap

from election.models import ElectionConfig
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


def _region_pages(base: str) -> list[str]:
    return [base, f"{base}/resultaten"]


class RegionSitemap(FrontendSitemap):
    """The CSB, HSB and municipality pages, linked the way the frontend's region lists link them."""

    def items(self):
        paths = []
        for config in ElectionConfig.objects.order_by("-date"):
            regions = Region.objects.filter(election__election_config=config).select_related("csb").order_by("slug")
            for region in regions.filter(region_category=config.csb_type):
                paths += _region_pages(f"/{config.slug}/csb/{region.slug}")
            for region in hsb_kieskringen(regions):
                paths += _region_pages(f"/{config.slug}/hsb/{region.slug}")
            for region in regions.filter(region_category=RegionCategory.GEMEENTE):
                csb = f"/csb/{region.csb.slug}" if region.csb else ""
                paths += _region_pages(f"/{config.slug}/gsb/{region.slug}{csb}")
        return paths


sitemaps = {"verkiezingen": ElectionSitemap, "regios": RegionSitemap}
