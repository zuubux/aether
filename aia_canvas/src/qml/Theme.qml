pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Typography Stacks
    readonly property string fontCode: "'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace"
    readonly property string fontSans: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

    // Text Hierarchy
    readonly property color textPrimary: "#F8FAFC"
    readonly property color textSecondary: "#C9D1D9"
    readonly property color textMuted: "#94A3B8"
    readonly property color textDimmed: "#64748B"

    // Surface, Border & Interactive Tokens
    readonly property color surfaceBackground: "#0B0F19"
    readonly property color surfaceBorder: "#1e2430"
    readonly property color surfaceHovered: "#161c28"
    readonly property color surfaceButton: "#161B22"
    readonly property color surfaceButtonHover: "#21262D"
    readonly property color borderSubtle: "#30363D"
    readonly property color borderHover: "#38BDF8"
    readonly property color accentFocus: "#38BDF8"
    readonly property color accentSuccess: "#238636"
    readonly property color accentCyan: "#00F2FE"

    // Tendril Colors
    readonly property color tendrilExplicit: "#00F2FE"
    readonly property color tendrilSemantic: "#A855F7"
    readonly property color tendrilTemporal: "#F59E0B"
    readonly property color tendrilWikilink: "#76FF03"
    readonly property color tendrilFallback: "#78909C"

    // Tendril & Filament Geometry
    readonly property real tendrilStrokeExplicit: 2.2
    readonly property real tendrilStrokeSemantic: 1.8
    readonly property real tendrilStrokeHover: 2.5
    readonly property real tendrilStrokeSibling: 1.0

    // Tier Dimensions
    readonly property real tier4Width: 12
    readonly property real tier4Height: 12
    readonly property real tier4Radius: 6

    readonly property real tier3Width: 124
    readonly property real tier3Height: 22
    readonly property real tier3Radius: 6

    readonly property real tier2Width: 240
    readonly property real tier2Height: 68
    readonly property real tier2Radius: 8

    readonly property real tier1_5Width: 380
    readonly property real tier1_5Height: 280
    readonly property real tier1_5Radius: 12

    // Timers
    readonly property int dwellIntentMs: 300
    readonly property int dwellRichMs: 2000

    // Animations
    readonly property int animDuration: 220
    // We cannot use Easing.OutQuint directly in QtObject as a value type if we aren't careful, 
    // but we can just use an int for duration. The easing is an enum, so we can expose it as an int, 
    // Easing.OutQuint is an enum value.
    readonly property int animEasing: Easing.OutQuint

    // Semantic Badge Colors for file archetypes
    readonly property color badgePdf: "#EF4444"      // Crimson
    readonly property color badgeDoc: "#00E5FF"      // Cyan
    readonly property color badgeMedia: "#34D399"    // Emerald
    readonly property color badgeTable: "#FB7185"    // Warm Rose
    readonly property color badgeCode: "#A78BFA"     // Violet / Purple
    readonly property color badgeArchive: "#F59E0B"  // Amber
    readonly property color badgeDefault: "#94A3B8"  // Slate

    function getBadgeColor(ext, archetype) {
        var e = (ext || "").toLowerCase().replace(".", "");
        if (e === "pdf") return badgePdf;
        if (e === "md" || e === "txt" || e === "markdown") return badgeDoc;
        if (e === "png" || e === "jpg" || e === "jpeg" || e === "webp" || e === "gif" || e === "svg" || e === "ico") return badgeMedia;
        if (e === "csv" || e === "tsv" || e === "json") return badgeTable;
        if (e === "py" || e === "sh" || e === "js" || e === "ts" || e === "cpp" || e === "qml") return badgeCode;
        if (e === "zip" || e === "tar" || e === "gz" || e === "rar" || e === "7z") return badgeArchive;
        
        // Fallback checks using archetype
        var arch = (archetype || "").toLowerCase();
        if (arch === "pdf") return badgePdf;
        if (arch === "document" || arch === "text") return badgeDoc;
        if (arch === "image" || arch === "video" || arch === "media") return badgeMedia;
        if (arch === "table" || arch === "dataset") return badgeTable;
        if (arch === "code") return badgeCode;
        if (arch === "archive") return badgeArchive;
        
        return badgeDefault;
    }

    function normalizeExt(ext) {
        var e = (ext || "").toLowerCase().replace(".", "").trim();
        if (e === "jpeg") return "JPG";
        if (e === "markdown") return "MD";
        if (e === "python") return "PY";
        if (e === "javascript") return "JS";
        if (e === "typescript") return "TS";
        return e.substring(0, 3).toUpperCase();
    }
}
