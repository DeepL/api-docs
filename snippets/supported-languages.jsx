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
    // Quick "hide noisy entries" toggles that supplement the resource +
    // feature checkboxes below.
    const [hideBeta, setHideBeta] = useState(false)
    const [hideExternal, setHideExternal] = useState(false)
    // Filter checkboxes split into two groups: one per /v3/languages
    // resource (does the resource list this lang?), one per API feature
    // key (does any resource report this feature for the lang?). Keys
    // match the API exactly so it is obvious which slice each filter
    // selects.
    const [resourceFilters, setResourceFilters] = useState({
        translate_text: false,
        translate_document: false,
        voice: false,
        write: false,
        glossary: false,
        style_rules: false,
        translation_memory: false,
    })
    const [featureFilters, setFeatureFilters] = useState({
        auto_detection: false,
        formality: false,
        tag_handling: false,
        writing_style: false,
        tone: false,
        transcription: false,
        translated_speech: false,
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
            {"lang": "ace", "name": "Acehnese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "af", "name": "Afrikaans", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "an", "name": "Aragonese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ar", "name": "Arabic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "as", "name": "Assamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ay", "name": "Aymara", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "az", "name": "Azerbaijani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ba", "name": "Bashkir", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "be", "name": "Belarusian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "bg", "name": "Bulgarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "bho", "name": "Bhojpuri", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "bn", "name": "Bengali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "br", "name": "Breton", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "bs", "name": "Bosnian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ca", "name": "Catalan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ceb", "name": "Cebuano", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ckb", "name": "Kurdish (Sorani)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "cs", "name": "Czech", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "cy", "name": "Welsh", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "da", "name": "Danish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "el", "name": "Greek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "en-GB", "name": "English (British)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "en-US", "name": "English (American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "eo", "name": "Esperanto", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "es-419", "name": "Spanish (Latin American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "et", "name": "Estonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "eu", "name": "Basque", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "fa", "name": "Persian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "fi", "name": "Finnish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ga", "name": "Irish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "gl", "name": "Galician", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "gn", "name": "Guarani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "gom", "name": "Konkani", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "gu", "name": "Gujarati", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ha", "name": "Hausa", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "he", "name": "Hebrew", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "hi", "name": "Hindi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "hr", "name": "Croatian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ht", "name": "Haitian Creole", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "hu", "name": "Hungarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "hy", "name": "Armenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "id", "name": "Indonesian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ig", "name": "Igbo", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "is", "name": "Icelandic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "jv", "name": "Javanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ka", "name": "Georgian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "kk", "name": "Kazakh", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "kmr", "name": "Kurdish (Kurmanji)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ky", "name": "Kyrgyz", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "la", "name": "Latin", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "lb", "name": "Luxembourgish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "lmo", "name": "Lombard", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ln", "name": "Lingala", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "lt", "name": "Lithuanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "lv", "name": "Latvian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "mai", "name": "Maithili", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "mg", "name": "Malagasy", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "mi", "name": "Maori", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "mk", "name": "Macedonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ml", "name": "Malayalam", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "mn", "name": "Mongolian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "mr", "name": "Marathi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ms", "name": "Malay", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "mt", "name": "Maltese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "my", "name": "Burmese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "nb", "name": "Norwegian (bokmål)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ne", "name": "Nepali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "nl", "name": "Dutch", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "oc", "name": "Occitan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "om", "name": "Oromo", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "pa", "name": "Punjabi", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "pag", "name": "Pangasinan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "pam", "name": "Kapampangan", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "pl", "name": "Polish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "prs", "name": "Dari", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ps", "name": "Pashto", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "pt", "name": "Portuguese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "pt-BR", "name": "Portuguese (Brazilian)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "pt-PT", "name": "Portuguese (European)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "qu", "name": "Quechua", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ro", "name": "Romanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ru", "name": "Russian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sa", "name": "Sanskrit", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "scn", "name": "Sicilian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "sk", "name": "Slovak", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sl", "name": "Slovenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sq", "name": "Albanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "sr", "name": "Serbian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "st", "name": "Sesotho", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "su", "name": "Sundanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "sv", "name": "Swedish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "sw", "name": "Swahili", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "ta", "name": "Tamil", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "te", "name": "Telugu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "tg", "name": "Tajik", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "th", "name": "Thai", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "tk", "name": "Turkmen", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "tl", "name": "Tagalog", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "tn", "name": "Tswana", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "tr", "name": "Turkish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "tt", "name": "Tatar", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "uk", "name": "Ukrainian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "ur", "name": "Urdu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "uz", "name": "Uzbek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "vi", "name": "Vietnamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "wo", "name": "Wolof", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "xh", "name": "Xhosa", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "yi", "name": "Yiddish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "yue", "name": "Cantonese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}}},
            {"lang": "zh-Hans", "name": "Chinese (simplified)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "zh-Hant", "name": "Chinese (traditional)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}}},
            {"lang": "zu", "name": "Zulu", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}}},
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
            {"lang": "ar", "name": "Arabic", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "bg", "name": "Bulgarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "bn", "name": "Bengali", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "cs", "name": "Czech", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "da", "name": "Danish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "de", "name": "German", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "el", "name": "Greek", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "en", "name": "English", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "en-GB", "name": "English (British)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "en-US", "name": "English (American)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "es", "name": "Spanish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "et", "name": "Estonian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "fi", "name": "Finnish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "fr", "name": "French", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "ga", "name": "Irish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "he", "name": "Hebrew", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "hr", "name": "Croatian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "hu", "name": "Hungarian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "id", "name": "Indonesian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "it", "name": "Italian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "ja", "name": "Japanese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "ko", "name": "Korean", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "lt", "name": "Lithuanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "lv", "name": "Latvian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "mt", "name": "Maltese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "nb", "name": "Norwegian (bokmål)", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "nl", "name": "Dutch", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "pl", "name": "Polish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "pt", "name": "Portuguese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "pt-BR", "name": "Portuguese (Brazilian)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "pt-PT", "name": "Portuguese (European)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"formality": {"status": "stable"}, "glossary": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "ro", "name": "Romanian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "ru", "name": "Russian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "formality": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "sk", "name": "Slovak", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "sl", "name": "Slovenian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}}},
            {"lang": "sv", "name": "Swedish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "th", "name": "Thai", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "tl", "name": "Tagalog", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"transcription": {"status": "stable", "external": true}}},
            {"lang": "tr", "name": "Turkish", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "uk", "name": "Ukrainian", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "vi", "name": "Vietnamese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "transcription": {"status": "stable", "external": true}, "translated_speech": {"status": "beta", "external": true}}},
            {"lang": "zh", "name": "Chinese", "status": "stable", "usable_as_source": true, "usable_as_target": true, "features": {"auto_detection": {"status": "stable"}, "glossary": {"status": "stable"}, "spoken_terms": {"status": "beta"}, "transcription": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "zh-Hans", "name": "Chinese (simplified)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
            {"lang": "zh-Hant", "name": "Chinese (traditional)", "status": "stable", "usable_as_source": false, "usable_as_target": true, "features": {"glossary": {"status": "stable"}, "translated_speech": {"status": "beta"}}},
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
        const resourceNames = Object.keys(RESOURCES)
        // For each resource, the set of langs it includes.
        const langsByResource = {}
        for (const r of resourceNames) {
            langsByResource[r] = new Set((RESOURCES[r] || []).map(e => e.lang))
        }
        // For each lang, the union of features across every resource it
        // appears in. We keep `status` and `external` per feature so the
        // table can flag beta / external-provider features in the UI.
        // If the same feature key appears in multiple resources, prefer
        // the more "interesting" signal (non-stable status, external=true
        // sticks) so the badge surfaces the caveat rather than hiding it.
        const featuresByLang = {}
        for (const r of resourceNames) {
            for (const e of (RESOURCES[r] || [])) {
                const slot = featuresByLang[e.lang] || (featuresByLang[e.lang] = {})
                for (const [k, v] of Object.entries(e.features || {})) {
                    const prev = slot[k] || { has: true, status: 'stable', external: false }
                    slot[k] = {
                        has: true,
                        status: v?.status !== 'stable' ? (v?.status || 'stable') : prev.status,
                        external: Boolean(v?.external) || prev.external,
                    }
                }
            }
        }

        const rows = tt.map(entry => {
            const resources = {}
            for (const r of resourceNames) {
                resources[r] = langsByResource[r].has(entry.lang)
            }
            return {
                code: entry.lang.toUpperCase(),
                name: entry.name,
                isVariant: !entry.usable_as_source && entry.usable_as_target,
                isBeta: entry.status !== 'stable',
                resources,
                features: featuresByLang[entry.lang] || {},
            }
        })
        rows.sort((a, b) => {
            if (a.isVariant !== b.isVariant) return a.isVariant ? 1 : -1
            return a.code < b.code ? -1 : a.code > b.code ? 1 : 0
        })
        return rows
    }, [])

    const filteredData = useMemo(() => {
        const anyResource = Object.values(resourceFilters).some(Boolean)
        let filtered = tableRows.filter(lang => {
            const matchesSearch = lang.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                lang.code.toLowerCase().includes(searchTerm.toLowerCase())
            const matchesResourceFilters = Object.keys(resourceFilters).every(key => {
                if (!resourceFilters[key]) return true
                // Customization keys can be sourced from either a resource
                // (glossary/style_rules/translation_memory) or a feature
                // (spoken_terms). langHasCustomization() handles both.
                const present = Boolean(lang.resources[key]) || Boolean(lang.features[key]?.has)
                if (!present) return false
                if (hideBeta && lang.isBeta) return false
                return true
            })
            // Feature filters only apply when at least one resource filter is
            // active, so an unrelated feature checkbox left toggled does not
            // silently exclude everything. When hide-external / hide-beta
            // is on, treat the corresponding features as unsupported here
            // too so the filter agrees with what the tick shows.
            const matchesFeatureFilters = !anyResource || Object.keys(featureFilters).every(key => {
                if (!featureFilters[key]) return true
                const info = lang.features[key]
                if (!info?.has) return false
                if (hideExternal && info.external) return false
                if (hideBeta && (info.status !== 'stable' || lang.isBeta)) return false
                return true
            })
            return matchesSearch && matchesResourceFilters && matchesFeatureFilters
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
    }, [tableRows, searchTerm, sortBy, sortOrder, resourceFilters, featureFilters, hideBeta, hideExternal])

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

    const toggleResourceFilter = (key) => {
        // Resource is single-select (one product at a time); customization
        // is multi-select. After any change, drop customizations that are
        // not compatible with the currently-selected resource (no language
        // is in both), matching the "available" rule used by the filter UI.
        const RESOURCE_KEYS = RESOURCE_OPTIONS.map(o => o.key)
        const CUSTOMIZATION_KEYS = CUSTOMIZATION_OPTIONS.map(o => o.key)
        const inResources = RESOURCE_KEYS.includes(key)
        const inCustomizations = CUSTOMIZATION_KEYS.includes(key)
        const turningOff = resourceFilters[key]
        const next = { ...resourceFilters }
        if (inResources) {
            for (const k of RESOURCE_KEYS) next[k] = false
            if (!turningOff) next[key] = true
        } else if (inCustomizations) {
            next[key] = !turningOff
        }
        const r = RESOURCE_KEYS.find(k => next[k])
        if (r) {
            for (const c of CUSTOMIZATION_KEYS) {
                if (next[c] && !customizationResources(c).has(r)) {
                    next[c] = false
                }
            }
        }
        setResourceFilters(next)
        // Voice is meaningful only with transcription support, so force
        // the transcription feature filter on as long as voice is the
        // active resource and clear it again when leaving voice.
        if (r === 'voice') {
            setFeatureFilters(prev => prev.transcription ? prev : { ...prev, transcription: true })
        } else {
            setFeatureFilters(prev => prev.transcription ? { ...prev, transcription: false } : prev)
        }
    }
    const toggleFeatureFilter = (key) => {
        setFeatureFilters(prev => ({ ...prev, [key]: !prev[key] }))
    }
    const clearMap = (setter, current) => {
        const cleared = {}
        for (const k of Object.keys(current)) cleared[k] = false
        setter(cleared)
    }
    const clearAllFilters = () => {
        setSearchTerm('')
        clearMap(setResourceFilters, resourceFilters)
        clearMap(setFeatureFilters, featureFilters)
        setHideBeta(false)
        setHideExternal(false)
    }

    const SortIcon = ({ column }) => {
        if (sortBy !== column) {
            return <span className="text-zinc-400">↕</span>
        }
        return <span className="text-zinc-600 dark:text-zinc-300">{sortOrder === 'asc' ? '↑' : '↓'}</span>
    }

    // Compact voice-style ticks for the table cells.
    //   ✓  stable, provided by DeepL
    //   ⎋  provided by an external service partner (voice.mdx legend)
    //   β  superscript on either symbol when the feature's status is not stable
    //   —  not available
    const ResourceTick = ({ on, beta }) => {
        // Treat beta as unsupported when the "hide beta" toggle is on.
        if (!on || (beta && hideBeta)) {
            return <span className="text-zinc-400 dark:text-zinc-500" title="Not available">—</span>
        }
        return (
            <span className="text-green-700 dark:text-green-400" title={beta ? 'Provided by DeepL (beta)' : 'Provided by DeepL'}>
                ✓{beta && <sup className="text-[0.7em] font-medium opacity-80">β</sup>}
            </span>
        )
    }
    const FeatureTick = ({ info, langBeta }) => {
        if (!info || !info.has) {
            return <span className="text-zinc-400 dark:text-zinc-500" title="Not available">—</span>
        }
        const beta = info.status !== 'stable' || langBeta
        // Mask externally-provided or beta features when the matching
        // "hide" toggle is on so the user can quickly see "what does
        // DeepL itself support, with no external partner / no beta?".
        if ((info.external && hideExternal) || (beta && hideBeta)) {
            return <span className="text-zinc-400 dark:text-zinc-500" title="Not available">—</span>
        }
        const cls = info.external
            ? 'text-amber-700 dark:text-amber-300'
            : 'text-green-700 dark:text-green-400'
        const titleParts = [info.external ? 'Provided by an external service partner' : 'Provided by DeepL']
        if (beta) titleParts.push(info.status)
        return (
            <span className={cls} title={titleParts.join(' · ')}>
                {info.external ? '⎋' : '✓'}
                {beta && <sup className="text-[0.7em] font-medium opacity-80">β</sup>}
            </span>
        )
    }

    const activeResourceCount = Object.values(resourceFilters).filter(Boolean).length
    const activeFeatureCount = Object.values(featureFilters).filter(Boolean).length
    const activeFiltersCount = activeResourceCount + activeFeatureCount + (hideBeta ? 1 : 0) + (hideExternal ? 1 : 0)
    const hasAnyFilter = activeFiltersCount > 0 || searchTerm.length > 0

    // `label` is the long form used in the filter UI; `short` is what the
    // table column header shows.
    const RESOURCE_OPTIONS = [
        { key: 'translate_text', label: 'Text translation', short: 'Text', link: '/api-reference/translate' },
        { key: 'translate_document', label: 'Document translation', short: 'Documents', link: '/api-reference/document' },
        { key: 'voice', label: 'Voice', short: 'Voice', link: '/api-reference/voice' },
        { key: 'write', label: 'Text improvement (Write)', short: 'Write', link: '/api-reference/improve-text' },
    ]
    const CUSTOMIZATION_OPTIONS = [
        { key: 'glossary', label: 'Glossaries', short: 'Glossaries', link: '/api-reference/multilingual-glossaries' },
        { key: 'style_rules', label: 'Style rules', short: 'Style rules', link: '/api-reference/style-rules' },
        { key: 'translation_memory', label: 'Translation memory', short: 'Translation memory', link: '/docs/learning-how-tos/examples-and-guides/how-to-use-translation-memories' },
        { key: 'spoken_terms', label: 'Spoken terms', short: 'Spoken terms', link: 'api-reference/voice#customization' },
    ]
    // `glossary` and `style_rules` features are intentionally absent here
    // because the matching customization columns already cover them.
    const FEATURE_OPTIONS = [
        { key: 'auto_detection', label: 'Auto-detection' },
        { key: 'transcription', label: 'Transcription' },
        { key: 'tag_handling', label: 'Tag handling', link: '/docs/xml-and-html-handling/xml' },
        { key: 'translated_speech', label: 'Translated speech' },
        { key: 'formality', label: 'Formality' },
        { key: 'tone', label: 'Tone' },
        { key: 'writing_style', label: 'Writing style' },
    ]
    // Which features each /v3/languages resource may report. Computed from
    // the inlined RESOURCES so it stays accurate without a hand-maintained
    // mapping; if the API adds a new feature to a resource the table picks
    // it up on the next refresh.
    const featuresByResource = useMemo(() => {
        const out = {}
        for (const [resource, entries] of Object.entries(RESOURCES)) {
            const set = new Set()
            for (const e of (entries || [])) {
                for (const k of Object.keys(e.features || {})) set.add(k)
            }
            out[resource] = set
        }
        return out
    }, [])

    // Feature filters are only meaningful for an explicitly selected
    // Resource is single-select; customization is multi-select. Both
    // groups are independent — picking a customization does not clear
    // the active resource and vice versa.
    const selectedResource = RESOURCE_OPTIONS.find(o => resourceFilters[o.key]) || null
    const selectedCustomizationKeys = CUSTOMIZATION_OPTIONS
        .filter(o => resourceFilters[o.key])
        .map(o => o.key)
    const anyResourceSelected = !!selectedResource
    // Which resources surface each customization. For glossary and
    // style_rules this is derivable from /v3/languages (the feature key
    // appears on the resource). translation_memory is not yet exposed as
    // a feature, so its applicable resources are listed explicitly until
    // the API catches up.
    const CUSTOMIZATION_APPLIES_TO_OVERRIDE = {
        translation_memory: new Set(['translate_text']),
    }
    const customizationResources = (key) => {
        const explicit = CUSTOMIZATION_APPLIES_TO_OVERRIDE[key]
        if (explicit) return explicit
        const set = new Set()
        for (const o of RESOURCE_OPTIONS) {
            if (featuresByResource[o.key]?.has(key)) set.add(o.key)
        }
        return set
    }
    // A customization is "available" when no resource is selected (the
    // table answers "what does each customization touch?") or when the
    // selected resource lists it as a feature (the table answers "which
    // langs work with this customization for this resource?").
    const customizationAvailable = (key) => {
        if (!selectedResource) return true
        return customizationResources(key).has(selectedResource.key)
    }
    // Whether a language is touched by a customization. Most
    // customizations are themselves /v3/languages resources, so we read
    // `lang.resources[key]`. `spoken_terms` is currently only exposed as
    // a feature on the voice resource, so we also check the feature map
    // as a fallback. The two channels are mutually exclusive in practice.
    const langHasCustomization = (lang, key) =>
        Boolean(lang.resources[key]) || Boolean(lang.features[key]?.has)
    // Feature filters are only meaningful when an actual product resource
    // is selected (customizations have no feature object of their own).
    const featureAvailable = (key) => {
        if (!selectedResource) return false
        return Boolean(featuresByResource[selectedResource.key]?.has(key))
    }
    // Voice ⇒ transcription is required, so the checkbox is forced on
    // and not togglable. The filter logic still treats it as a normal
    // feature filter; this only locks the UI control.
    const featureLocked = (key) =>
        selectedResource?.key === 'voice' && key === 'transcription'
    // Features to display in the table's "Features" column for the
    // currently-active resource. Empty when no resource is selected.
    const visibleFeatureKeys = selectedResource
        ? FEATURE_OPTIONS.filter(o => featureAvailable(o.key)).map(o => o.key)
        : []
    const showFeaturesColumn = !!selectedResource
    // Selecting a resource collapses the resource columns to just the
    // selected one; same for customization. The two groups are
    // independent so picking a customization does not hide the resource
    // columns and vice versa — except that picking only a customization
    // (with no resource) hides the resource columns altogether, because
    // the user has already narrowed the question to that customization.
    const visibleResourceOptions = selectedResource
        ? [selectedResource]
        : (selectedCustomizationKeys.length > 0 ? [] : RESOURCE_OPTIONS)
    const visibleCustomizationOptions = selectedCustomizationKeys.length > 0
        ? CUSTOMIZATION_OPTIONS.filter(o => selectedCustomizationKeys.includes(o.key))
        : (selectedResource
            ? CUSTOMIZATION_OPTIONS.filter(o => customizationAvailable(o.key))
            : CUSTOMIZATION_OPTIONS)

    const renderResourceCellItems = (options) => (lang) => (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
            {options.map(({ key, label }) => (
                <span key={key} className="inline-flex items-center gap-1">
                    <span className="text-zinc-700 dark:text-zinc-300">{label}</span>
                    <ResourceTick on={langHasCustomization(lang, key)} beta={lang.isBeta} />
                </span>
            ))}
        </div>
    )
    const ResourceCell = renderResourceCellItems(RESOURCE_OPTIONS)
    const CustomizationCell = renderResourceCellItems(CUSTOMIZATION_OPTIONS)
    const FeaturesCell = (lang) => {
        if (visibleFeatureKeys.length === 0) return null
        return (
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
                {visibleFeatureKeys.map(key => {
                    const opt = FEATURE_OPTIONS.find(o => o.key === key)
                    const label = opt ? opt.label : key
                    return (
                        <span key={key} className="inline-flex items-center gap-1">
                            <span className="text-zinc-700 dark:text-zinc-300">{label}</span>
                            <FeatureTick info={lang.features[key]} langBeta={lang.isBeta} />
                        </span>
                    )
                })}
            </div>
        )
    }

    const renderFilterCheckbox = (state, toggle, isEnabled = () => true, isLocked = () => false) => ({ key, label, link }) => {
        const enabled = isEnabled(key)
        const locked = isLocked(key)
        const checked = locked ? true : (enabled && state[key])
        const interactive = enabled && !locked
        return (
            <label
                key={key}
                title={
                    locked
                        ? 'Required for the selected resource'
                        : enabled ? undefined : 'Select a matching resource to enable this filter'
                }
                className={`flex items-center space-x-2 rounded-md px-3 py-2 transition-colors ${
                    locked
                        ? 'bg-blue-50 dark:bg-blue-900/30 ring-1 ring-blue-300 dark:ring-blue-700 cursor-not-allowed opacity-80'
                        : !enabled
                            ? 'opacity-50 cursor-not-allowed'
                            : checked
                                ? 'bg-blue-50 dark:bg-blue-900/30 ring-1 ring-blue-300 dark:ring-blue-700 cursor-pointer'
                                : 'hover:bg-zinc-100 dark:hover:bg-zinc-700/50 cursor-pointer'
                }`}
            >
                <input
                    type="checkbox"
                    disabled={!interactive}
                    checked={checked}
                    onChange={() => interactive && toggle(key)}
                    className="rounded border-zinc-300 text-blue-600 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-700 disabled:cursor-not-allowed"
                />
                <span className={`text-sm ${
                    checked
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
        )
    }

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

                <div className="bg-zinc-50 dark:bg-zinc-800/50 p-4 rounded-lg border border-zinc-200 dark:border-zinc-700 space-y-4">
                    <div className="flex flex-row items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-3">
                            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                                Filters
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
                        <div className="flex items-center gap-4">
                            <label className="flex items-center gap-1.5 text-xs cursor-pointer text-zinc-700 dark:text-zinc-300">
                                <input
                                    type="checkbox"
                                    checked={hideBeta}
                                    onChange={() => setHideBeta(v => !v)}
                                    className="rounded border-zinc-300 text-blue-600 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-700"
                                />
                                Hide beta
                            </label>
                            <label className="flex items-center gap-1.5 text-xs cursor-pointer text-zinc-700 dark:text-zinc-300">
                                <input
                                    type="checkbox"
                                    checked={hideExternal}
                                    onChange={() => setHideExternal(v => !v)}
                                    className="rounded border-zinc-300 text-blue-600 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-700"
                                />
                                Hide external
                            </label>
                        </div>
                    </div>

                    <div>
                        <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase mb-2">
                            By resource
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {RESOURCE_OPTIONS.map(renderFilterCheckbox(resourceFilters, toggleResourceFilter))}
                        </div>
                    </div>

                    <div>
                        <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase mb-2">
                            By customization
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {CUSTOMIZATION_OPTIONS.map(renderFilterCheckbox(resourceFilters, toggleResourceFilter, customizationAvailable))}
                        </div>
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase">
                                By feature
                            </span>
                            {!anyResourceSelected && (
                                <span className="text-[10px] text-zinc-400 dark:text-zinc-500">
                                    Pick a resource to enable feature filters
                                </span>
                            )}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {FEATURE_OPTIONS.map(renderFilterCheckbox(featureFilters, toggleFeatureFilter, featureAvailable, featureLocked))}
                        </div>
                    </div>
                </div>

                <div className="text-sm text-zinc-500 dark:text-zinc-400">
                    Showing {filteredData.length} of {tableRows.length} languages
                    {activeFiltersCount > 0 && ` (${activeFiltersCount} filter${activeFiltersCount > 1 ? 's' : ''} active)`}
                </div>
            </div>

            <div className="hidden sm:block">
                <table className="w-full divide-y divide-zinc-200 dark:divide-zinc-700" aria-label="DeepL API supported languages and features">
                    <thead className="bg-zinc-50 dark:bg-zinc-800">
                        <tr>
                            <th
                                className="w-px whitespace-nowrap px-1.5 py-1.5 text-left text-[10px] font-medium text-zinc-500 dark:text-zinc-300 uppercase cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700"
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
                                className="w-px whitespace-nowrap px-1.5 py-1.5 text-left text-[10px] font-medium text-zinc-500 dark:text-zinc-300 uppercase cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700"
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
                            {visibleResourceOptions.map(o => (
                                <th key={`h-res-${o.key}`} className="w-px whitespace-nowrap px-0.5 py-1.5 text-center text-[10px] font-medium text-zinc-500 dark:text-zinc-300 uppercase">
                                    {o.short}
                                </th>
                            ))}
                            {visibleCustomizationOptions.map(o => (
                                <th key={`h-cust-${o.key}`} className="w-px whitespace-nowrap px-1 py-1.5 text-center text-[10px] font-medium text-zinc-500 dark:text-zinc-300 uppercase">
                                    {o.short}
                                </th>
                            ))}
                            {visibleFeatureKeys.map(key => {
                                const o = FEATURE_OPTIONS.find(opt => opt.key === key)
                                return (
                                    <th key={`h-feat-${key}`} className="w-px whitespace-nowrap px-1 py-1.5 text-center text-[10px] font-medium text-zinc-500 dark:text-zinc-300 uppercase">
                                        {o ? o.label : key}
                                    </th>
                                )
                            })}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-zinc-200 dark:bg-zinc-900 dark:divide-zinc-700">
                        {filteredData.map((lang) => (
                            <tr key={lang.code} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                                <td className="w-px whitespace-nowrap px-1.5 py-1.5 text-xs font-mono text-zinc-900 dark:text-zinc-100">
                                    <code className="bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-[11px]">
                                        {lang.code}
                                    </code>
                                </td>
                                <td className="w-px whitespace-nowrap px-1.5 py-1.5 text-sm text-zinc-900 dark:text-zinc-100">
                                    {lang.name}
                                    {lang.isVariant && (
                                        <span
                                            className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/50 dark:text-orange-200"
                                            title="This language variant can only be used as a target language, not as a source."
                                        >
                                            target only
                                        </span>
                                    )}
                                </td>
                                {visibleResourceOptions.map(o => (
                                    <td key={`c-res-${o.key}`} className="px-0.5 py-1.5 text-center text-sm">
                                        <ResourceTick on={Boolean(lang.resources[o.key])} beta={lang.isBeta} />
                                    </td>
                                ))}
                                {visibleCustomizationOptions.map(o => (
                                    <td key={`c-cust-${o.key}`} className="px-1 py-1.5 text-center text-sm">
                                        <ResourceTick on={langHasCustomization(lang, o.key)} beta={lang.isBeta} />
                                    </td>
                                ))}
                                {visibleFeatureKeys.map(key => (
                                    <td key={`c-feat-${key}`} className="px-1 py-1.5 text-center text-sm">
                                        <FeatureTick info={lang.features[key]} langBeta={lang.isBeta} />
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="sm:hidden space-y-2">
                {filteredData.map((lang) => (
                    <div
                        key={lang.code}
                        className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-3 bg-white dark:bg-zinc-900 space-y-2"
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                                {lang.name}
                                {lang.isVariant && (
                                    <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/50 dark:text-orange-200">
                                        target only
                                    </span>
                                )}
                            </span>
                            <code className="bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded text-xs font-mono text-zinc-700 dark:text-zinc-300">
                                {lang.code}
                            </code>
                        </div>
                        <div>
                            <div className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase mb-0.5">Resource</div>
                            {ResourceCell(lang)}
                        </div>
                        <div>
                            <div className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase mb-0.5">Customization</div>
                            {CustomizationCell(lang)}
                        </div>
                        {showFeaturesColumn && (
                            <div>
                                <div className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase mb-0.5">Features</div>
                                {FeaturesCell(lang)}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {filteredData.length === 0 && (
                <div className="text-center py-8 text-zinc-500 dark:text-zinc-400">
                    No languages found matching your criteria.
                </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
                <span><span className="text-green-700 dark:text-green-400 font-medium">✓</span> Provided by DeepL</span>
                <span><span className="text-amber-700 dark:text-amber-300 font-medium">⎋</span> Provided by an external service partner</span>
                <span><span className="text-zinc-400 dark:text-zinc-500 font-medium">—</span> Not available</span>
                <span><sup className="font-medium">β</sup> Beta / early-access (alongside ✓ or ⎋)</span>
            </div>
        </div>
    )
}
