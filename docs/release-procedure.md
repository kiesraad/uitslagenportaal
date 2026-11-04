## Release Procedure

### Dev/staging releases

The CD pipeline automatically deploys development and staging releases for each commit to the `dev` and `main` branch respectively. 
They are identified by their git commit sha hash or `git describe --tags --long --always`.

### Production releases

> [!NOTE]
> This section is WIP since we don't have a production environment yet

For production deploys follow these steps:

1. Make sure the version of the code is merged to `main` and deployed on the staging environment.
2. Test the changes that are included in the release on the staging environment.
   A way to see all new changes is by drafting a release through GitHub, targeting the `main` branch and auto-generating release notes. 
   Make sure to use the version tag which the new release will get, using the version scheme as described below.
3. Finalize the draft release or add the release, if none was drafted, in GitHub. 
   This will create the tag and trigger the production CD pipeline.
4. Merge the tag back in `dev`, so a `git describe` uses the latest tag. 
   Due to write limitations, this is usually only possible by creating a PR from `main` to `dev`.
   Make sure to not use a squash/rebase merge, or the tag won't be synced to `dev`.
5. Test the production environment.

### Versioning scheme

Use the following version scheme: `v[year].[month].[version within month]`, e.g. `v2028.4.0`.

The version within a month starts at `0`, so a second release in April 2028 is `v2028.4.1`.
Always give all three numbers and no leading zeros (`v2028.04.0` and `v2028.4` are invalid):
the pipeline fails a tag that doesn't match before it publishes any image.
The images get the version without the `v` (`2028.4.0`) and the `prod` tag.
