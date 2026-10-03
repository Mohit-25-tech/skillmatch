# Design decisions for a viva

1. **A workspace first, with a separate landing page.** The default screen demonstrates the product immediately. The public landing page explains the journey, while the dashboard supports repeat use.
2. **Quiet surfaces, focused accents.** Dark neutral cards reduce visual noise. Violet signals actions and skill intelligence; mint marks positive alignment. Color is reinforced by text and icons.
3. **Transparent scores.** A hybrid score combines meaning (65%) with explicit skill evidence (35%). The interface shows components and declares keyword-only fallback. A percentage is an alignment signal, not a probability of getting hired.
4. **A bounded skill dictionary.** spaCy PhraseMatcher makes extraction reproducible and explainable. Aliases improve practical recall without requiring a proprietary language model. This trades open-ended inference for auditability.
5. **Progressive visual enhancement.** CSS creates the base constellation; Three.js enhances it. Reduced-motion and low-power devices retain the same content without WebGL. GPU resources are released on navigation.
6. **Small reusable frontend modules.** TypeScript provides strict contracts, jQuery handles DOM/events/AJAX as required, and dynamic imports separate heavy visuals from the initial page.
7. **Access tokens in memory.** An HttpOnly cookie stores the rotating refresh token. Logout increments an account version to invalidate existing access tokens. Public registration cannot create an administrator.
8. **Managed database, minimal local pooling.** Neon’s pooler handles serverless connections. SQLAlchemy NullPool avoids holding additional idle connections in the API process. SQLite makes tests independent and fast.
9. **Ownership is enforced on the server.** Candidates cannot read others’ resumes; recruiters only manage their own jobs/applicants. UI visibility is a convenience, never the authorization boundary.
10. **Synthetic data is labeled.** The preview provides an immediate experience without inventing actual vacancies, user activity, or live AI results. Course charts explain the limitations of their generated dataset.
11. **Archive jobs; delete private resumes.** Job closure preserves application history. Resume deletion cascades related private records to avoid retaining stale personal material.
12. **Accessibility is part of implementation.** Semantic forms, focus rings, skip navigation, touch controls, named icons, responsive layouts, and reduced-motion handling are built into components rather than added as a separate mode.
