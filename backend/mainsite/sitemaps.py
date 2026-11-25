from django.contrib.sitemaps import Sitemap

from election.models import ElectionConfig


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


sitemaps = {"verkiezingen": ElectionSitemap}
