## Owner live replay continuation

After changing the explicit site envelope to 50×100 m and using a warehouse brief that leaves final clear height / structural system / wall build-up to later engineering, production no longer failed first on `OUTSIDE_SITE`. It failed with the durable message mapped from `PLAN_GEOMETRY_DIMENSION_NOT_SPECIFIED`: some building heights or wall thicknesses in the generated plan were missing/invalid; no revision was saved.

This confirms a second independent stage-boundary gap after issue #154. The brief explicitly says final clear height and fire/racking/structural requirements are to be determined engineering-wise. Those unknowns must not be invented. At the same time, their absence should not prevent pre-approval Program/Zoning/Design Options/2D review when the horizontal operational layout is otherwise valid. They must become blocking before Frozen Baseline approval intended for BIM/3D, because downstream 3D is not allowed to invent them.

The prior uploaded-plan `PLAN_SOURCE_GEOMETRY_INCOMPLETE` screenshot is a separate source-reading path and must not be conflated with this warehouse generation failure.
