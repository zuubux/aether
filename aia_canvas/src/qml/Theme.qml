pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Typography Stacks
    readonly property string fontCode: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Consolas', monospace"
    readonly property string fontSans: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    readonly property string fontBody: fontSans

    // Centralized AI Typographic Tokens
    readonly property font fontAiBody: Qt.font({ family: "Inter", pixelSize: 13, weight: Font.Normal })
    readonly property font fontAiCode: Qt.font({ family: "JetBrains Mono", pixelSize: 12, weight: Font.Normal })

    // Text Hierarchy
    readonly property color textPrimary: "#F8FAFC"
    readonly property color textSecondary: "#C9D1D9"
    readonly property color textMuted: "#94A3B8"
    readonly property color textDimmed: "#64748B"

    // Dynamic Rich Snippet Palette
    readonly property string snippetCss: "<style>" +
        ".label { color: " + textDimmed + "; font-size: 11px; font-weight: 600; }" +
        ".val { color: " + textPrimary + "; }" +
        ".arrow { color: " + accentFocus + "; }" +
        ".dot { color: " + textDimmed + "; }" +
        ".date { color: " + textMuted + "; }" +
        ".subject { color: " + textPrimary + "; font-weight: normal; }" +
        ".body-text { color: " + textSecondary + "; margin-top: 10px; }" +
        ".wikilink { color: " + accentFocus + "; font-weight: 600; text-decoration: none; }" +
        "</style>"

    // Surface, Border & Interactive Tokens
    readonly property color surfaceBackground: "#0B0F19"
    readonly property color surfaceGlass: "#E80D1117"
    readonly property color surfaceDrawer: Qt.rgba(0.07, 0.08, 0.10, 0.85)
    readonly property color surfaceElevated: "#161B22"
    readonly property color surfaceBar: Qt.rgba(0.04, 0.04, 0.05, 0.95)
    readonly property color borderSeamSubtle: Qt.rgba(1.0, 1.0, 1.0, 0.06)
    readonly property color surfaceBorder: "#1e2430"
    readonly property color surfaceHovered: "#161c28"
    readonly property color surfaceButton: "#161B22"
    readonly property color surfaceButtonHover: "#21262D"
    readonly property color borderSubtle: "#30363D"
    readonly property color borderHover: "#38BDF8"
    readonly property color accentShell: "#F59E0B"
    readonly property color accentFocus: "#38BDF8"
    readonly property color accentSuccess: "#238636"
    readonly property color accentCyan: "#00F2FE"

    // Conversational Design Tokens
    readonly property color accentGemini: "#38BDF8"
    readonly property color accentClaude: "#F97316"
    readonly property color accentAI: "#38BDF8"
    readonly property color accentRed: "#EF4444"
    readonly property color surfaceDialogue: Qt.rgba(0.07, 0.08, 0.10, 0.85)

    // ANSI Palette Tokens
    readonly property color ansiRed: "#EF4444"
    readonly property color ansiGreen: "#10B981"
    readonly property color ansiYellow: "#F59E0B"
    readonly property color ansiBlue: "#60A5FA"
    readonly property color ansiMagenta: "#C084FC"
    readonly property color ansiCyan: "#06B6D4"
    readonly property color ansiGray: "#71717A"

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

    readonly property real tier1_5Width: 440
    readonly property real tier1_5Height: 320
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
    readonly property color badgeDocx: "#3B82F6"     // Blue
    readonly property color badgePptx: "#F97316"     // Orange
    readonly property color badgeSpreadsheet: "#10B981" // Emerald
    readonly property color badgeSvg: "#F43F5E"      // Rose
    readonly property color badgeNotebook: "#EC4899" // Pink
    readonly property color badgeDatabase: "#8B5CF6" // Purple
    readonly property color badgeMedia: "#34D399"    // Emerald
    readonly property color badgeAudio: "#F59E0B"    // Amber / Gold
    readonly property color badgeVideo: "#10B981"    // Emerald / Green
    readonly property color badgeTable: "#FB7185"    // Warm Rose
    readonly property color badgeCode: "#A78BFA"     // Violet / Purple
    readonly property color badgeArchive: "#F59E0B"  // Amber
    readonly property color badgeVdf: "#0284C7"      // Steam Blue
    readonly property color badgeReg: "#A855F7"      // Registry Purple
    readonly property color badgeJson: "#F59E0B"     // Amber
    readonly property color badgeYaml: "#8B5CF6"     // Violet
    readonly property color badgeToml: "#6366F1"     // Indigo
    readonly property color badgeCsv: "#10B981"      // Emerald
    readonly property color badgeSql: "#3B82F6"      // Blue
    readonly property color badgeDocker: "#06B6D4"   // Cyan
    readonly property color badgeBinary: "#64748B"   // Slate Gray
    readonly property color badgePcap: "#0D9488"     // Teal
    readonly property color badgeDisk: "#4F46E5"     // Indigo
    readonly property color badge3d: "#EA580C"       // Orange/Bronze
    readonly property color badgeExe: "#6366F1"      // Indigo/Purple
    readonly property color badgeGdoc: "#4285F4"     // Google Blue
    readonly property color badgeGsheet: "#34A853"   // Google Green
    readonly property color badgeGslides: "#FBBC05"  // Google Amber/Yellow
    readonly property color badgeGdraw: "#EA4335"    // Google Red
    readonly property color badgeDefault: "#94A3B8"  // Slate

    function getBadgeColor(ext, archetype) {
        var e = (ext || "").toLowerCase().replace(/^\./, "").trim();
        if (e === "svg") return badgeSvg;
        if (e === "pdf") return badgePdf;
        if (e === "docx") return badgeDocx;
        if (e === "pptx" || e === "ppt" || e === "odp") return badgePptx;
        if (e === "xlsx" || e === "xls" || e === "ods") return badgeSpreadsheet;
        if (e === "ipynb") return badgeNotebook;
        if (e === "sqlite" || e === "db") return badgeDatabase;
        if (e === "md" || e === "txt" || e === "markdown") return badgeDoc;
        if (e === "mp3" || e === "wav" || e === "flac" || e === "ogg" || e === "m4a" || e === "aac") return badgeAudio;
        if (e === "mp4" || e === "mkv" || e === "webm" || e === "mov" || e === "avi") return badgeVideo;
        if (e === "png" || e === "jpg" || e === "jpeg" || e === "webp" || e === "gif" || e === "ico") return badgeMedia;
        if (e === "json") return badgeJson;
        if (e === "yaml" || e === "yml") return badgeYaml;
        if (e === "toml") return badgeToml;
        if (e === "csv" || e === "tsv") return badgeCsv;
        if (e === "sql") return badgeSql;
        if (e === "dockerfile" || e === "docker" || e === "containerfile" || e === "compose") return badgeDocker;
        if (e === "py" || e === "sh" || e === "js" || e === "ts" || e === "cpp" || e === "qml") return badgeCode;
        if (e === "pcap" || e === "pcapng") return badgePcap;
        if (e === "iso" || e === "img") return badgeDisk;
        if (e === "stl" || e === "obj" || e === "step") return badge3d;
        if (e === "exe" || e === "dll") return badgeExe;
        if (e === "so" || e === "dylib" || e === "bin" || e === "parquet" || e === "gcode") return badgeBinary;
        if (e === "vdf" || e === "acf") return badgeVdf;
        if (e === "reg") return badgeReg;
        if (e === "gdoc") return badgeGdoc;
        if (e === "gsheet") return badgeGsheet;
        if (e === "gslides") return badgeGslides;
        if (e === "gdraw") return badgeGdraw;
        if (e === "zip" || e === "tar" || e === "gz" || e === "tgz" || e === "bz2" || e === "xz" || e === "whl" || e === "jar" || e === "epub" || e === "rar" || e === "7z" || e.indexOf("tar.") !== -1) return badgeArchive;
        
        // Fallback checks using archetype
        var arch = (archetype || "").toLowerCase();
        if (arch === "pdf") return badgePdf;
        if (arch === "docx") return badgeDocx;
        if (arch === "pptx" || arch === "presentation") return badgePptx;
        if (arch === "xlsx" || arch === "spreadsheet") return badgeSpreadsheet;
        if (arch === "svg") return badgeSvg;
        if (arch === "notebook") return badgeNotebook;
        if (arch === "database") return badgeDatabase;
        if (arch === "document" || arch === "text") return badgeDoc;
        if (arch === "audio") return badgeAudio;
        if (arch === "video") return badgeVideo;
        if (arch === "image" || arch === "media" || arch === "asset") return badgeMedia;
        if (arch === "table" || arch === "dataset") return badgeTable;
        if (arch === "code") return badgeCode;
        if (arch === "archive") return badgeArchive;
        if (arch === "binary") return badgeBinary;
        
        return badgeDefault;
    }

    function normalizeExt(ext) {
        var e = (ext || "").toLowerCase().replace(/^\./, "").trim();
        if (e === "svg") return "SVG";
        if (e === "xlsx") return "XLSX";
        if (e === "pptx") return "PPTX";
        if (e === "ods") return "ODS";
        if (e === "odp") return "ODP";
        if (e === "jpeg") return "JPG";
        if (e === "markdown") return "MD";
        if (e === "python") return "PY";
        if (e === "javascript") return "JS";
        if (e === "typescript") return "TS";
        if (e === "json") return "JSON";
        if (e === "yaml" || e === "yml") return "YAML";
        if (e === "toml") return "TOML";
        if (e === "csv") return "CSV";
        if (e === "tsv") return "TSV";
        if (e === "sql") return "SQL";
        if (e === "dockerfile" || e === "docker" || e === "containerfile") return "DOCKER";
        if (e === "compose") return "COMPOSE";
        if (e === "tar" || e === "tar.gz" || e === "tgz" || e === "tar.bz2" || e === "tar.xz" || e === "gz" || e === "bz2" || e === "xz") return "TAR";
        if (e === "zip" || e === "archive") return "ZIP";
        if (e === "whl") return "WHL";
        if (e === "vdf") return "VDF";
        if (e === "acf") return "ACF";
        if (e === "reg") return "REG";
        if (e === "jar") return "JAR";
        if (e === "epub") return "EPUB";
        if (e === "pcap" || e === "pcapng") return "PCAP";
        if (e === "iso" || e === "img") return "DISK";
        if (e === "stl" || e === "obj" || e === "step") return "3D";
        if (e === "exe") return "EXE";
        if (e === "dll") return "DLL";
        if (e === "so" || e === "dylib" || e === "bin") return "BIN";
        if (e === "gcode") return "CNC";
        if (e === "parquet") return "PARQUET";
        if (e === "gdoc") return "GDOC";
        if (e === "gsheet") return "GSHEET";
        if (e === "gslides") return "GSLIDES";
        if (e === "gdraw") return "GDRAW";
        return e.substring(0, 3).toUpperCase();
    }

    function getOmniGlowColor(query) {
        if (!query) return borderSubtle;
        var q = (query || "").trim();
        if (q.startsWith(">")) return accentShell; // Amber for Shell
        if (q.startsWith("?")) return accentAI; // Cyan/Indigo for LLM
        if (q.startsWith("/")) return "#10B981"; // Emerald for System
        return borderSubtle; // Neutral slate for Search
    }
}
