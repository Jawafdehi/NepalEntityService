Help me complete /Users/kwame/Documents/projects/newnepal2/workspaces/jawafdehi/services/NepalEntityService/migrations/010-source-2082-direct-candidates.

This module will import candidates in /Users/kwame/Documents/projects/newnepal2/workspaces/jawafdehi/services/NepalEntityService/migrations/010-source-2082-direct-candidates/data/DirectElectionResultCentral2082.json to the system.

The election hasn't happened yet, so votes will be 0.

Some candidates already exist in the system, others do not. In /Users/kwame/Documents/projects/newnepal2/workspaces/jawafdehi/services/NepalEntityService/migrations/010-source-2082-direct-candidates/data/candidate_id_matches_2079_2082.csv, we need to match the Candidate ID (from electoral history). If candidates exist, we just update the electoral history. Otheriwse, we would have to create a new entity.

As always, before creating new entities, we have to prepare slugs and make sure they do not collide.

We also have to prepare a generate translations file.

Also, we do not source personal information anymor; see: /Users/kwame/Documents/projects/newnepal2/workspaces/jawafdehi/services/NepalEntityService/migrations/007-redact-family-info.

For instructions on how to seed, please see: /Users/kwame/Documents/projects/newnepal2/workspaces/jawafdehi/services/NepalEntityService/migrations/005-seed-2079-election-candidates

## Notes

1. Whean reading DirectElectionResultCentral2082.json, Political party names should be formatted to the equivalent of:
df["PoliticalPartyName"].str.replace("(एकल चुनाव चिन्ह)", "").str.strip()

2. It is best to begin by loading all entities of type person into memory.

3. For slug matching for district/political party, /Users/kwame/Documents/projects/newnepal2/workspaces/jawafdehi/services/NepalEntityService/migrations/010-source-2082-direct-candidates/data/district-to-slug.csv and /Users/kwame/Documents/projects/newnepal2/workspaces/jawafdehi/services/NepalEntityService/migrations/010-source-2082-direct-candidates/data/candidate_id_matches_2079_2082.csv already have the enough information to convert test to slug or NES ID. For districts, the NES id is entity:location/district/slug and for partieis, it is entity:organization/political_party/slug.

Read the 2082.json using utf-8-sig encoding.