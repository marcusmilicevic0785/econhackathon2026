# Library intervention analysis

## Status: not estimated

No library treatment effect or event-study graph is available. The downloaded library locations and facility snapshots don't establish when services changed, which areas were affected, or what happened to a consistent outcome before and after the change.

The missing pieces are:

- Verified dates and details for branch openings, closures or sustained changes in hours.
- Repeated, directly observed outcomes on consistent geography.
- Credible comparison areas and enough independent treatment locations for inference.

Current directories from [NYPL](https://www.nypl.org/locations), [Brooklyn Public Library](https://www.bklynlibrary.org/locations) and [Queens Public Library](https://www.queenslibrary.org/about-us/locations) locate branches, but don't by themselves supply that history.

CDC PLACES models local prevalence from survey and demographic inputs. It isn't suitable for measuring the effects of a local library programme; see the [dataset warning](https://catalog.data.gov/dataset/places-local-data-for-better-health-census-tract-data-2025-release). Overlapping ACS five-year estimates and current facility snapshots also don't provide the required outcome panel.

The existing [NYC access analysis](nyc_equity.md) is cross-sectional and answers a different question. No difference-in-differences coefficient, event-study estimate or power calculation has been produced. The [model status file](../../outputs/model_status.json) records this analysis as `not_estimated`.
