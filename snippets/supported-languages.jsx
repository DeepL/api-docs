/**
 * Render a list (or the full interactive table) of DeepL-supported
 * languages drawn from the vended /v3/languages responses inlined
 * below. The component is sandboxed by Mintlify, so the data has to
 * ship inside this file; see `scripts/fetch_v3_languages.py` for how
 * the `RESOURCES` block is refreshed.
 *
 * Drop the component wherever you would have hand-typed a language
 * list. It must appear at the block level (its own line); MDX does
 * not honour component references mid-paragraph.
 *
 * Props
 * -----
 * mode: 'inline' (default) | 'bullets' | 'table'
 *   - 'inline'  - comma-separated `<code>{lang}</code>` list. Use for
 *                 prose like "supported target languages: `de`, `en`, ..."
 *   - 'bullets' - vertical bulleted list of `<code>{lang}</code> ({name})`.
 *                 Use for API parameter docs where each language has a
 *                 sub-bullet.
 *   - 'table'   - the full interactive sortable / filterable table.
 *                 The `resource`, `feature`, `direction`, and
 *                 `includeBeta` props are ignored in this mode; the
 *                 table merges signals across every relevant resource.
 *
 * resource: string (required for 'inline' and 'bullets')
 *   Name of the /v3/languages resource to read from. Must match a
 *   key in the inlined `RESOURCES` object — i.e. one of
 *   `translate_text`, `translate_document`, `voice`, `write`,
 *   `glossary`, `style_rules`, or `translation_memory`. When omitted,
 *   the component falls back to `translate_text` so the call still
 *   renders, but you almost always want to set this explicitly so the
 *   list matches the feature you are documenting.
 *
 * feature: string (optional)
 *   API feature key to filter by, exactly as it appears in the
 *   `features` object of a /v3/languages response (snake_case). Only
 *   languages that list this feature in their `features` object are
 *   included. Examples by resource:
 *     - translate_text / translate_document: 'auto_detection',
 *       'formality', 'glossary', 'style_rules', 'tag_handling'
 *     - write: 'auto_detection', 'tone', 'writing_style'
 *     - voice: 'auto_detection', 'formality', 'glossary',
 *       'transcription', 'translated_speech'
 *   Omit the prop to include every language in the chosen resource.
 *
 * direction: 'source' | 'target' (optional)
 *   - 'source' keeps languages with `usable_as_source: true`.
 *   - 'target' keeps languages with `usable_as_target: true`.
 *   Omit to include both. Use this whenever the feature is
 *   directional (e.g. style_rules / writing_style / tone are
 *   target-only; auto_detection is source-only).
 *
 * includeBeta: boolean (default false)
 *   When true, also include languages whose `status` is not
 *   'stable' (e.g. 'beta' or 'early_access'). The hourly refresh
 *   already vends languages and features at every status, so this
 *   prop just chooses what to show.
 *
 * Examples
 * --------
 *   <SupportedLanguages mode="table" />
 *
 *   <SupportedLanguages
 *     resource="translate_text"
 *     feature="style_rules"
 *     direction="target"
 *   />
 *
 *   <SupportedLanguages
 *     mode="bullets"
 *     resource="write"
 *     feature="writing_style"
 *     direction="target"
 *   />
 */
export const SupportedLanguages = ({
    mode = 'inline',
    resource,
    feature,
    direction,
    includeBeta = false,
}) => {
    const [searchTerm, setSearchTerm] = useState('')
    const [sortBy, setSortBy] = useState('name')
    const [sortOrder, setSortOrder] = useState('asc')
    const [featureFilters, setFeatureFilters] = useState({
        translation: false,
        glossary: false,
        tagHandling: false,
        textImprovement: false,
        translationMemory: false,
        styleRules: false
    })

    // The RESOURCES object below is the inlined output of running
    // `scripts/fetch_v3_languages.py` against `data/v3-languages/`.
    // Each key matches a /v3/languages resource and each value is the
    // verbatim JSON array returned by `GET /v3/languages?resource=<name>`.
    // BEGIN GENERATED: RESOURCES (do not edit; run scripts/fetch_v3_languages.py)
    const RESOURCES = {
        "glossary": [
            {"lang": "ar", "name": "Arabic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "bg", "name": "Bulgarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "cs", "name": "Czech", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "da", "name": "Danish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "el", "name": "Greek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "et", "name": "Estonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "fi", "name": "Finnish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "he", "name": "Hebrew", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "hu", "name": "Hungarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "id", "name": "Indonesian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "lt", "name": "Lithuanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "lv", "name": "Latvian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "nb", "name": "Norwegian (bokmål)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "nl", "name": "Dutch", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "pl", "name": "Polish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "pt", "name": "Portuguese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ro", "name": "Romanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ru", "name": "Russian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "sk", "name": "Slovak", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "sl", "name": "Slovenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "sv", "name": "Swedish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "tr", "name": "Turkish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "uk", "name": "Ukrainian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "vi", "name": "Vietnamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
        ],
        "style_rules": [
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
        ],
        "translate_document": [
            {"lang": "ace", "name": "Acehnese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "af", "name": "Afrikaans", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "an", "name": "Aragonese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ar", "name": "Arabic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "as", "name": "Assamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ay", "name": "Aymara", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "az", "name": "Azerbaijani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ba", "name": "Bashkir", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "be", "name": "Belarusian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "bg", "name": "Bulgarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "bho", "name": "Bhojpuri", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "bn", "name": "Bengali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "br", "name": "Breton", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "bs", "name": "Bosnian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ca", "name": "Catalan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ceb", "name": "Cebuano", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ckb", "name": "Kurdish (Sorani)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "cs", "name": "Czech", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "cy", "name": "Welsh", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "da", "name": "Danish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "el", "name": "Greek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "en-GB", "name": "English (British)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "en-US", "name": "English (American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "eo", "name": "Esperanto", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "es-419", "name": "Spanish (Latin American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "et", "name": "Estonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "eu", "name": "Basque", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "fa", "name": "Persian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "fi", "name": "Finnish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ga", "name": "Irish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "gl", "name": "Galician", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "gn", "name": "Guarani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "gom", "name": "Konkani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "gu", "name": "Gujarati", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ha", "name": "Hausa", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "he", "name": "Hebrew", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "hi", "name": "Hindi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "hr", "name": "Croatian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ht", "name": "Haitian Creole", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "hu", "name": "Hungarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "hy", "name": "Armenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "id", "name": "Indonesian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ig", "name": "Igbo", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "is", "name": "Icelandic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "jv", "name": "Javanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ka", "name": "Georgian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "kk", "name": "Kazakh", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "kmr", "name": "Kurdish (Kurmanji)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ky", "name": "Kyrgyz", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "la", "name": "Latin", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "lb", "name": "Luxembourgish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "lmo", "name": "Lombard", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ln", "name": "Lingala", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "lt", "name": "Lithuanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "lv", "name": "Latvian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "mai", "name": "Maithili", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "mg", "name": "Malagasy", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "mi", "name": "Maori", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "mk", "name": "Macedonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ml", "name": "Malayalam", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "mn", "name": "Mongolian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "mr", "name": "Marathi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ms", "name": "Malay", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "mt", "name": "Maltese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "my", "name": "Burmese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "nb", "name": "Norwegian (bokmål)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ne", "name": "Nepali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "nl", "name": "Dutch", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "oc", "name": "Occitan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "om", "name": "Oromo", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "pa", "name": "Punjabi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "pag", "name": "Pangasinan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "pam", "name": "Kapampangan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "pl", "name": "Polish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "prs", "name": "Dari", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ps", "name": "Pashto", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "pt", "name": "Portuguese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "pt-BR", "name": "Portuguese (Brazilian)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "pt-PT", "name": "Portuguese (European)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "qu", "name": "Quechua", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ro", "name": "Romanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ru", "name": "Russian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sa", "name": "Sanskrit", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "scn", "name": "Sicilian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "sk", "name": "Slovak", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sl", "name": "Slovenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sq", "name": "Albanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "sr", "name": "Serbian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "st", "name": "Sesotho", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "su", "name": "Sundanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "sv", "name": "Swedish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sw", "name": "Swahili", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ta", "name": "Tamil", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "te", "name": "Telugu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "tg", "name": "Tajik", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "th", "name": "Thai", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "tk", "name": "Turkmen", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "tl", "name": "Tagalog", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "tn", "name": "Tswana", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "tr", "name": "Turkish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "tt", "name": "Tatar", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "uk", "name": "Ukrainian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ur", "name": "Urdu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "uz", "name": "Uzbek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "vi", "name": "Vietnamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "wo", "name": "Wolof", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "xh", "name": "Xhosa", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "yi", "name": "Yiddish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "yue", "name": "Cantonese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "zh-Hans", "name": "Chinese (simplified)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "zh-Hant", "name": "Chinese (traditional)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "zu", "name": "Zulu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
        ],
        "translate_text": [
            {"lang": "ace", "name": "Acehnese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "af", "name": "Afrikaans", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "an", "name": "Aragonese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ar", "name": "Arabic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "as", "name": "Assamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ay", "name": "Aymara", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "az", "name": "Azerbaijani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ba", "name": "Bashkir", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "be", "name": "Belarusian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "bg", "name": "Bulgarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "bho", "name": "Bhojpuri", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "bn", "name": "Bengali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "br", "name": "Breton", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "bs", "name": "Bosnian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ca", "name": "Catalan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ceb", "name": "Cebuano", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ckb", "name": "Kurdish (Sorani)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "cs", "name": "Czech", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "cy", "name": "Welsh", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "da", "name": "Danish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "de-CH", "name": "German (Swiss)", "status": "beta", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "beta"}, "glossary": {"status": "beta"}, "tag_handling": {"status": "beta"}}},
            {"lang": "de-DE", "name": "German", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "el", "name": "Greek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "en-GB", "name": "English (British)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "en-US", "name": "English (American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "eo", "name": "Esperanto", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "es-419", "name": "Spanish (Latin American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "et", "name": "Estonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "eu", "name": "Basque", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "fa", "name": "Persian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "fi", "name": "Finnish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "fr-CA", "name": "French (Canadian)", "status": "beta", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "beta"}, "glossary": {"status": "beta"}, "style_rules": {"status": "beta"}, "tag_handling": {"status": "beta"}}},
            {"lang": "fr-FR", "name": "French", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ga", "name": "Irish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "gl", "name": "Galician", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "gn", "name": "Guarani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "gom", "name": "Konkani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "gu", "name": "Gujarati", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ha", "name": "Hausa", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "he", "name": "Hebrew", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "hi", "name": "Hindi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "hr", "name": "Croatian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ht", "name": "Haitian Creole", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "hu", "name": "Hungarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "hy", "name": "Armenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "id", "name": "Indonesian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ig", "name": "Igbo", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "is", "name": "Icelandic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "jv", "name": "Javanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ka", "name": "Georgian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "kk", "name": "Kazakh", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "kmr", "name": "Kurdish (Kurmanji)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ky", "name": "Kyrgyz", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "la", "name": "Latin", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "lb", "name": "Luxembourgish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "lmo", "name": "Lombard", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ln", "name": "Lingala", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "lt", "name": "Lithuanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "lv", "name": "Latvian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "mai", "name": "Maithili", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "mg", "name": "Malagasy", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "mi", "name": "Maori", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "mk", "name": "Macedonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ml", "name": "Malayalam", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "mn", "name": "Mongolian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "mr", "name": "Marathi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ms", "name": "Malay", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "mt", "name": "Maltese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "my", "name": "Burmese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "nb", "name": "Norwegian (bokmål)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ne", "name": "Nepali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "nl", "name": "Dutch", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "oc", "name": "Occitan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "om", "name": "Oromo", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "pa", "name": "Punjabi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "pag", "name": "Pangasinan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "pam", "name": "Kapampangan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "pl", "name": "Polish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "prs", "name": "Dari", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ps", "name": "Pashto", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "pt", "name": "Portuguese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "pt-BR", "name": "Portuguese (Brazilian)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "pt-PT", "name": "Portuguese (European)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "qu", "name": "Quechua", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ro", "name": "Romanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ru", "name": "Russian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "sa", "name": "Sanskrit", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "scn", "name": "Sicilian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "sk", "name": "Slovak", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "sl", "name": "Slovenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "sq", "name": "Albanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "sr", "name": "Serbian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "st", "name": "Sesotho", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "su", "name": "Sundanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "sv", "name": "Swedish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "sw", "name": "Swahili", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ta", "name": "Tamil", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "te", "name": "Telugu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "tg", "name": "Tajik", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "th", "name": "Thai", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "tk", "name": "Turkmen", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "tl", "name": "Tagalog", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "tn", "name": "Tswana", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "tr", "name": "Turkish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ts", "name": "Tsonga", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "tt", "name": "Tatar", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "uk", "name": "Ukrainian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "ur", "name": "Urdu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "uz", "name": "Uzbek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "vi", "name": "Vietnamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "wo", "name": "Wolof", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "xh", "name": "Xhosa", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "yi", "name": "Yiddish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "yue", "name": "Cantonese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "zh-Hans", "name": "Chinese (simplified)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "zh-Hant", "name": "Chinese (traditional)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "style_rules": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
            {"lang": "zu", "name": "Zulu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tag_handling": {"status": "stable"}}},
        ],
        "translation_memory": [
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "en-GB", "name": "English (British)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {}},
            {"lang": "en-US", "name": "English (American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "es-419", "name": "Spanish (Latin American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {}},
            {"lang": "zh-Hans", "name": "Chinese (simplified)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {}},
        ],
        "voice": [
            {"lang": "ar", "name": "Arabic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "bg", "name": "Bulgarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "bn", "name": "Bengali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "cs", "name": "Czech", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "da", "name": "Danish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "el", "name": "Greek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "en-GB", "name": "English (British)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "en-US", "name": "English (American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "et", "name": "Estonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "fi", "name": "Finnish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "ga", "name": "Irish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "he", "name": "Hebrew", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "hr", "name": "Croatian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "hu", "name": "Hungarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "id", "name": "Indonesian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "lt", "name": "Lithuanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "lv", "name": "Latvian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "mt", "name": "Maltese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "nb", "name": "Norwegian (bokmål)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "nl", "name": "Dutch", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "pl", "name": "Polish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "pt", "name": "Portuguese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "pt-BR", "name": "Portuguese (Brazilian)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "pt-PT", "name": "Portuguese (European)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "ro", "name": "Romanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "ru", "name": "Russian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "sk", "name": "Slovak", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "sl", "name": "Slovenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "sv", "name": "Swedish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "th", "name": "Thai", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "tl", "name": "Tagalog", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "tr", "name": "Turkish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "uk", "name": "Ukrainian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "vi", "name": "Vietnamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "stable", "external": true}}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "zh-Hans", "name": "Chinese (simplified)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
            {"lang": "zh-Hant", "name": "Chinese (traditional)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "stable"}}},
        ],
        "write": [
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "tone": {"status": "stable"}, "writing_style": {"status": "stable"}}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "en-GB", "name": "English (British)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"tone": {"status": "stable"}, "writing_style": {"status": "stable"}}},
            {"lang": "en-US", "name": "English (American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"tone": {"status": "stable"}, "writing_style": {"status": "stable"}}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "pt", "name": "Portuguese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "pt-BR", "name": "Portuguese (Brazilian)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {}},
            {"lang": "pt-PT", "name": "Portuguese (European)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "zh-Hans", "name": "Chinese (simplified)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {}},
        ],
    }
    // END GENERATED

    // ------------------------------------------------------------------
    // mode === 'inline' | 'bullets': render a comma list / bullet list of
    // codes drawn directly from the named resource's response.
    // ------------------------------------------------------------------
    const inlineRows = useMemo(() => {
        const entries = (resource && RESOURCES[resource]) || RESOURCES.translate_text || []
        return entries.filter(entry => {
            const features = entry.features || {}
            if (!includeBeta && entry.status !== 'stable') return false
            if (direction === 'source' && !entry.usable_as_source) return false
            if (direction === 'target' && !entry.usable_as_target) return false
            if (feature && !features[feature]) return false
            return true
        })
    }, [resource, feature, direction, includeBeta])

    // ------------------------------------------------------------------
    // mode === 'table': derive a single flat row per language, merging
    // signals from every relevant resource.
    // ------------------------------------------------------------------
    const tableRows = useMemo(() => {
        const tt = RESOURCES.translate_text || []
        const writeSet = new Set((RESOURCES.write || []).map(e => e.lang))
        const glossarySet = new Set((RESOURCES.glossary || []).map(e => e.lang))
        const tmSet = new Set((RESOURCES.translation_memory || []).map(e => e.lang))
        const rows = tt.map(entry => {
            const features = entry.features || {}
            return {
                code: entry.lang.toUpperCase(),
                name: entry.name,
                translation: true,
                isVariant: !entry.usable_as_source && entry.usable_as_target,
                isBeta: entry.status !== 'stable',
                glossary: glossarySet.has(entry.lang),
                tagHandling: Boolean(features.tag_handling),
                textImprovement: writeSet.has(entry.lang),
                translationMemory: tmSet.has(entry.lang),
                styleRules: Boolean(features.style_rules),
            }
        })
        rows.sort((a, b) => {
            if (a.isVariant !== b.isVariant) return a.isVariant ? 1 : -1
            return a.code < b.code ? -1 : a.code > b.code ? 1 : 0
        })
        return rows
    }, [])

    const filteredData = useMemo(() => {
        let filtered = tableRows.filter(lang => {
            const matchesSearch = lang.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                lang.code.toLowerCase().includes(searchTerm.toLowerCase())
            const matchesFeatureFilters = Object.keys(featureFilters).every(key => {
                if (!featureFilters[key]) return true
                return lang[key] === true
            })
            return matchesSearch && matchesFeatureFilters
        })
        filtered.sort((a, b) => {
            let aValue, bValue
            if (sortBy === 'name') {
                aValue = a.name.toLowerCase()
                bValue = b.name.toLowerCase()
            } else if (sortBy === 'code') {
                aValue = a.code.toLowerCase()
                bValue = b.code.toLowerCase()
            }
            if (sortOrder === 'asc') {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
            }
            return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
        })
        return filtered
    }, [tableRows, searchTerm, sortBy, sortOrder, featureFilters])

    if (mode !== 'table') {
        if (mode === 'bullets') {
            return (
                <ul>
                    {inlineRows.map(entry => (
                        <li key={entry.lang}>
                            <code>{entry.lang}</code> ({entry.name})
                        </li>
                    ))}
                </ul>
            )
        }
        return (
            <span>
                {inlineRows.map((entry, i) => (
                    <span key={entry.lang}>
                        {i > 0 && ', '}
                        <code>{entry.lang}</code>
                    </span>
                ))}
            </span>
        )
    }

    // ------------------------------------------------------------------
    // mode === 'table': full interactive language table.
    // ------------------------------------------------------------------

    const handleSort = (column) => {
        if (sortBy === column) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(column)
            setSortOrder('asc')
        }
    }

    const handleFeatureFilterChange = (key) => {
        setFeatureFilters(prev => ({
            ...prev,
            [key]: !prev[key]
        }))
    }

    const clearAllFilters = () => {
        setSearchTerm('')
        setFeatureFilters({
            translation: false,
            glossary: false,
            tagHandling: false,
            textImprovement: false,
            translationMemory: false,
            styleRules: false
        })
    }

    const SortIcon = ({ column }) => {
        if (sortBy !== column) {
            return <span className="text-zinc-400">↕</span>
        }
        return <span className="text-zinc-600 dark:text-zinc-300">{sortOrder === 'asc' ? '↑' : '↓'}</span>
    }

    const FeatureBadges = ({ lang }) => {
        const features = [
            { key: 'translation', label: 'Translation', variant: lang.isVariant },
            { key: 'glossary', label: 'Glossaries' },
            { key: 'tagHandling', label: 'Tag Handling' },
            { key: 'textImprovement', label: 'Text Improvement' },
            { key: 'translationMemory', label: 'Translation Memory' },
            { key: 'styleRules', label: 'Style Rules' },
        ]
        return (
            <div className="flex flex-wrap gap-1.5">
                {lang.isBeta && (
                    <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-200"
                        title="This language is currently in beta. Characters translated into this language are not billed during the beta phase."
                    >
                        Beta
                    </span>
                )}
                {features.map(f => {
                    if (f.variant) {
                        return (
                            <span
                                key={f.key}
                                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/50 dark:text-orange-200"
                                title="This language variant can only be used as a target language, not as a source. For example, use EN as the source and EN-GB as the target."
                            >
                                Translation: Target Only
                            </span>
                        )
                    }
                    if (lang[f.key]) {
                        return (
                            <span key={f.key} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200">
                                {f.label}
                            </span>
                        )
                    }
                    return null
                })}
            </div>
        )
    }

    const activeFiltersCount = Object.values(featureFilters).filter(Boolean).length
    const hasAnyFilter = activeFiltersCount > 0 || searchTerm.length > 0

    return (
        <div className="not-prose">
            <div className="mb-6 space-y-4">
                <div className="flex-1">
                    <input
                        type="text"
                        placeholder="Search languages or codes..."
                        aria-label="Search languages or codes"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full px-4 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                    />
                </div>

                <div className="bg-zinc-50 dark:bg-zinc-800/50 p-4 rounded-lg border border-zinc-200 dark:border-zinc-700">
                    <div className="flex flex-row items-center justify-between mb-3">
                        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                            Filter by feature
                        </span>
                        {hasAnyFilter && (
                            <button
                                onClick={clearAllFilters}
                                className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 underline"
                            >
                                Clear all
                            </button>
                        )}
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
                        {[
                            { key: 'translation', label: 'Translation' },
                            { key: 'glossary', label: 'Glossaries' },
                            { key: 'tagHandling', label: 'Tag Handling', link: '/docs/xml-and-html-handling/xml' },
                            { key: 'textImprovement', label: 'Text Improvement', link: '/api-reference/improve-text' },
                            { key: 'translationMemory', label: 'Translation Memory', link: '/docs/learning-how-tos/examples-and-guides/how-to-use-translation-memories' },
                            { key: 'styleRules', label: 'Style Rules', link: '/api-reference/style-rules' }
                        ].map(({ key, label, link }) => (
                            <label
                                key={key}
                                className={`flex items-center space-x-2 cursor-pointer rounded-md px-3 py-2 transition-colors ${
                                    featureFilters[key]
                                        ? 'bg-blue-50 dark:bg-blue-900/30 ring-1 ring-blue-300 dark:ring-blue-700'
                                        : 'hover:bg-zinc-100 dark:hover:bg-zinc-700/50'
                                }`}
                            >
                                <input
                                    type="checkbox"
                                    checked={featureFilters[key]}
                                    onChange={() => handleFeatureFilterChange(key)}
                                    className="rounded border-zinc-300 text-blue-600 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-700"
                                />
                                <span className={`text-sm ${
                                    featureFilters[key]
                                        ? 'font-semibold text-blue-700 dark:text-blue-300'
                                        : 'text-zinc-700 dark:text-zinc-300'
                                }`}>
                                    {label}
                                </span>
                                {link && (
                                    <a
                                        href={link}
                                        onClick={(e) => e.stopPropagation()}
                                        className="ml-0.5 text-zinc-400 hover:text-blue-600 dark:hover:text-blue-400"
                                        title={`${label} docs`}
                                    >
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <circle cx="12" cy="12" r="10" />
                                            <line x1="12" y1="16" x2="12" y2="12" />
                                            <line x1="12" y1="8" x2="12.01" y2="8" />
                                        </svg>
                                    </a>
                                )}
                            </label>
                        ))}
                    </div>
                </div>

                <div className="text-sm text-zinc-500 dark:text-zinc-400">
                    Showing {filteredData.length} of {tableRows.length} languages
                    {activeFiltersCount > 0 && ` (${activeFiltersCount} filter${activeFiltersCount > 1 ? 's' : ''} active)`}
                </div>
            </div>

            <div className="hidden sm:block">
                <table className="w-full divide-y divide-zinc-200 dark:divide-zinc-700" aria-label="DeepL API supported languages and features">
                    <thead className="bg-zinc-50 dark:bg-zinc-800 sticky top-0 z-10">
                        <tr>
                            <th
                                className="w-px whitespace-nowrap px-3 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-300 uppercase cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700"
                                onClick={() => handleSort('code')}
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('code') } }}
                                role="columnheader button"
                                tabIndex={0}
                                aria-sort={sortBy === 'code' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
                            >
                                <div className="flex items-center space-x-1">
                                    <span>Code</span>
                                    <SortIcon column="code" />
                                </div>
                            </th>
                            <th
                                className="w-px whitespace-nowrap px-3 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-300 uppercase cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700"
                                onClick={() => handleSort('name')}
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('name') } }}
                                role="columnheader button"
                                tabIndex={0}
                                aria-sort={sortBy === 'name' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
                            >
                                <div className="flex items-center space-x-1">
                                    <span>Language</span>
                                    <SortIcon column="name" />
                                </div>
                            </th>
                            <th className="px-3 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-300 uppercase">
                                Features
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-zinc-200 dark:bg-zinc-900 dark:divide-zinc-700">
                        {filteredData.map((lang) => (
                            <tr key={lang.code} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                                <td className="w-px whitespace-nowrap px-3 py-3 text-sm font-mono text-zinc-900 dark:text-zinc-100">
                                    <code className="bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded text-xs">
                                        {lang.code}
                                    </code>
                                </td>
                                <td className="w-px whitespace-nowrap px-3 py-3 text-sm text-zinc-900 dark:text-zinc-100">
                                    {lang.name}
                                </td>
                                <td className="px-3 py-3">
                                    <FeatureBadges lang={lang} />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="sm:hidden space-y-2">
                {filteredData.map((lang) => (
                    <div
                        key={lang.code}
                        className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-3 bg-white dark:bg-zinc-900"
                    >
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                                {lang.name}
                            </span>
                            <code className="bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded text-xs font-mono text-zinc-700 dark:text-zinc-300">
                                {lang.code}
                            </code>
                        </div>
                        <FeatureBadges lang={lang} />
                    </div>
                ))}
            </div>

            {filteredData.length === 0 && (
                <div className="text-center py-8 text-zinc-500 dark:text-zinc-400">
                    No languages found matching your criteria.
                </div>
            )}
        </div>
    )
}
