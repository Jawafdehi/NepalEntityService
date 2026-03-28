# Migration: 009-party-election-symbols

## Purpose

Add 2082 election symbol pictures to political parties in the Nepal Entity Service database. This migration enhances political party entities by linking them to their official election symbols, making the data more visually rich and useful for applications displaying party information.

The migration:
- Matches political party slugs with available election symbol images
- Adds EntityPicture objects with type SYMBOL to qualifying parties
- Uses the official 2082 election symbols hosted on the NES assets server

## Data Sources

- **existing-symbols.txt**: List of 137 available election symbol image files (PNG format)
- **NES Assets Server**: https://assets.nes.jawafdehi.org/assets/images/2082-election-symbols/
- **Nepal Election Commission**: Original source of election symbols for 2082 elections
- **Political Party Database**: Existing political parties in the NES database (151 total parties)

## Changes

This migration successfully updated 137 out of 151 political parties in the database:

**Updated Parties (137)**: Added EntityPicture objects with:
- Type: `EntityPictureType.SYMBOL`
- URL: `https://assets.nes.jawafdehi.org/assets/images/2082-election-symbols/{party-slug}.png`
- Description: "2082 Election Symbol"

**Skipped Parties (14)**: No matching symbol files available for:
- janaswaraj-party
- rastriya-ekata-party-prajatantrawadi
- nepal-communist-party-socialist
- janasamajbadi-party-nepal
- nepal-samajwadi-party-lohiyawadi
- ujyalo-nepal-party
- jai-janmabhumi-party-nepal
- nepal-communist-party-maoist-socialist
- nepal-communist-party-maoist-centre
- nepal-communist-party-unified-socialist
- nepal-communist-party-ekata-national-campaign
- nepal-rashtrawadi-party
- aam-aadmi-party-nepal
- national-motherland-party

**Database Impact**:
- 137 entity versions created (one per updated party)
- No new entities or relationships created
- All changes tracked with author "author:damodar-dahal"
- Change description: "Add 2082 election symbol pictures"

## Notes

- **Migration Performance**: Completed in 0.2 seconds, processing 151 political parties
- **Idempotent**: Safe to re-run - will only update parties that don't already have pictures
- **Symbol Matching**: Uses exact slug matching between party entities and symbol filenames
- **Asset Hosting**: All symbol images are hosted on the official NES assets server
- **Data Quality**: 90.7% coverage (137/151 parties) - missing symbols likely due to:
  - Parties registered after symbol collection
  - Name/slug variations between party registration and symbol files
  - Parties that may not have participated in 2082 elections

