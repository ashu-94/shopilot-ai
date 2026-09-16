# Storefront photography and color refresh

The 23 fictional catalog items now use locally served real photographs. These illustrate product categories; they are not manufacturer photos of the fictional product names, and do not validate catalog specifications. Product IDs and transactional data are unchanged.

Sources and links are maintained in `frontend/src/product-photos.json` and the public `/photo-credits.html` page. Twenty-one entries use Pexels photography under the [Pexels License](https://www.pexels.com/license/). The two UPS entries share the [GS-COM APC product photo](https://gs-com.bz/products/apc-850va-backup-ups); its commercial redistribution license was not verified. Obtain permission or replace those two photos before public commercial deployment. Attribution alone does not grant reuse rights.

Photographs are served locally with lazy loading and descriptive alternative text. Missing images fall back to a category icon and a Photo unavailable label. Card captions state Representative photo. The new palette uses indigo, peach, teal and golden yellow with readable text, responsive layouts and reduced-motion support.

Validation: production frontend build; all 23 images loaded; no horizontal overflow at 390 pixels; all four Playwright tests passed; zero axe violations in scanned states. Visual captures: `verification/storefront-desktop.png` and `verification/storefront-mobile.png`.
