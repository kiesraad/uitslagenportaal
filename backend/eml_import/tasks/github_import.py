from eml_import.utils.github_eml_importer import GithubEmlImporter

# todo: make Celery task once we have Celery configured
def import_next_eml_commit() -> int:
    return GithubEmlImporter().run()
