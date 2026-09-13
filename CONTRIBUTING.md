# Contributing

Please describe the concrete issue, proposed behavior and validation in your pull request. Useful contributions include source-preserving reconstruction, language-specific fluency review, complex-script rendering, admission checks and evaluation methods.

- Preserve numerical data, reference answers, protected label keys and source identities.
- Keep semantic generation/review in the configured API workflow; never adjust recovered data to fit a reference answer.
- Update executable prompt definitions and run `python scripts/export_prompts.py` to refresh readable snapshots.
- Run the offline tests documented in `docs/SETUP.md`. Do not require credentials in tests or CI.
- Never commit `.env`, API keys, request/response logs, downloaded/derived datasets, system fonts or private information. Use small synthetic examples to reproduce bugs.
- State uncertainty explicitly. Do not describe automated review as human certification or claim completed evaluation without results.

The code license is MIT. Retain existing notices and document any new dependency or asset license. Dataset redistribution is a separate decision from contributing pipeline code.
