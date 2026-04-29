# Anshuman Jena Project Context Index

This file is now a human-readable index only.

The active project context source for ResumeForge is:
- `inputs/project_profiles/`

Each project now has its own detailed markdown dossier:
- `inputs/project_profiles/01_askalpha.md`
- `inputs/project_profiles/02_cligenix.md`
- `inputs/project_profiles/03_quantum_portfolio.md`
- `inputs/project_profiles/04_fcoscraternet.md`
- `inputs/project_profiles/05_food_package_freshness.md`
- `inputs/project_profiles/06_mlops_heart_disease.md`
- `inputs/project_profiles/07_autonomous_navigation.md`
- `inputs/project_profiles/08_ironclad_agent.md`

Why this changed:
- The old single-file inventory was too thin for strong project bullet generation.
- The app now reads the full folder so the LLM gets richer repo-backed context per project.
- Numeric claims from the previous inventory were preserved inside the relevant project dossiers where needed.

If you want a single place to review the new content, open the files above in order.
