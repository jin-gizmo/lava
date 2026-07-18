# ex: sw=4 ts=4 et ai
# ------------------------------------------------------------------------------
# Makefile self-documenting help generator (POSIX awk compatible)
# See https://github.com/jin-gizmo/makehelp for more information.
#
# Version 2.0.0
#
#       If it ain't broke, it doesn't have enough features yet.
#
# Murray Andrews
#
# ------------------------------------------------------------------------------
# This script is really 1.5 scripts. It is first run in a "preprocess" mode with
# the output of `make -pn` as input to get the resolved make variable values.
# These are annotated with the `#:var` and `#:tvar` directives. This is then fed
# into the script again with the makefile content for help text generation.
# ------------------------------------------------------------------------------

BEGIN {
    DEBUG = ENVIRON["MAKEHELP_DEBUG"] + 0  # Enable / disable debugging output (use dprint())
    PRE = preprocess + 0  # Enable / disable preprocessor phase
    DEPENDENCY_RECURSION_LIMIT = 10
    DEPENDENCY_RESOLUTION = (resolve_dependencies != "") ? resolve_dependencies : "yes"
    DEFAULT_CATEGORY = default_category ? default_category : "Targets"
    DEFAULT_VAR_CATEGORY = default_var_category ? default_var_category : "Variables"
    # DEFAULT_VALUE is for unset variables. Variables explicitly set to empty
    # don't use this.
    # DEFAULT_VALUE = "..."
    DEFAULT_VALUE = ""
    HELP_CATEGORY = (help_category != "") ? help_category : DEFAULT_CATEGORY

    # Initialise state trackers. Pre* vars are for the preprocessor phase.
    PreState = ""
    PreTarget = ""

    LineContinuation = 0
    LineBuf = ""
    CurrentFile = "/"  # Sentinel
    RequiredArgs = ""
    OptionalArgs = ""
    TargetCategory = DEFAULT_CATEGORY
    VarCategory = DEFAULT_VAR_CATEGORY
    split("", GlobalMakeVars)       # #:var declarations : name --> value
    split("", TargetMakeVars)       # #:tvar declarations : (target, name) --> value
    split("", TargetCategoryIndex)  # #:cat category-name --> order of occurrence
    split("", TargetListByCat)      # (category, index) --> target
    split("", Descriptions)         # (category, target, line_num) --> string
    split("", DescriptionCount)     # (category, target) --> count of description lines
    split("", VarCategoryIndex)     # #:vcat category-name --> order of occurrence
    split("", VarDescriptions)      # (category, variable, line_num) --> string
    split("", VarDescriptionCount)  # (category, variable) --> count of description lines
    split("", TargetCount)          # category --> count of targets in category
    split("", TargetDeps)           # target --> dependency list
    split("", PendingReq)           # Accumulator : required var --> value
    split("", PendingOpt)           # Accumulator : optional var --> value
    split("", TargetReqVars)        # (tgt, required var) --> value-or-empty
    split("", TargetOptVars)        # (tgt, optional var) --> value-or-empty
    split("", ResolvedReq)          # After recursive resolution of dependencies.
    split("", ResolvedOpt)
    PrologueCount = 0
    EpilogueCount = 0

    # width can be set as command line var or we work it out ourself
    WIDTH = width > 0 ? width : tty_columns()
    if (WIDTH < 65) WIDTH = 65

    if (!PRE) {
        load_theme(theme)
        # Set hr to "no" on command line to disable horizontal lines.
        if (hr == "no") HR = ""
    }
}

# ------------------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------------------

# Format / theme setup
function load_theme(theme,    hr_span, t) {

    # Indents
    IN_L_CAT = 0    # Left indent for category headings
    IN_L_TGT = 4    # Left indent for targets / variables
    IN_L_DSC = 8    # Left indent for descriptions
    IN_R_DSC = 0    # Right indent for descriptions
    IN_L_LOG = 4    # Left indent for prologue and epilogue
    IN_R_LOG = 4    # Right indent for prologue and epilogue
    IN_L_HR = 4     # Left indent for horizontal rule
    IN_R_HR = 4     # Right indent for horizontal rule

    # Dark theme using 256 colours
    t = "dark"
    THEMES[t, "category"] = "\033[38;5;203;1m"  # vivid coral red, bold
    THEMES[t, "target"] = "\033[38;5;81m"       # turquoise / cyan
    THEMES[t, "argument"] = "\033[38;5;179m"    # soft yellow-orange
    THEMES[t, "value"] = "\033[38;5;179;4m"     # bright yellow + underline
    THEMES[t, "prologue"] = ""                  # Leave these or stuff breaks
    THEMES[t, "description"] = ""               # Leave these or stuff breaks
    THEMES[t, "warning"] = "\033[38;5;196;1;7m" # bright red + bold + reverse
    THEMES[t, "code"] = "\033[4;2m"             # underline for code in backticks
    THEMES[t, "code-reset"] = "\033[24;22m"
    THEMES[t, "bold"] = "\033[1m"
    THEMES[t, "bold-reset"] = "\033[22m"
    THEMES[t, "italic"] = "\033[3m"
    THEMES[t, "italic-reset"] = "\033[23m"
    THEMES[t, "underline"] = "\033[4m"
    THEMES[t, "underline-reset"] = "\033[24m"
    THEMES[t, "reset"] = "\033[0m"
    hr_span = spaces(WIDTH - IN_L_HR - IN_R_HR)
    gsub(/ /, "q", hr_span)
    THEMES[t, "hr"] = sprintf("%s\033[38;5;246m\033(0%s\033(B\033[0m", spaces(IN_L_HR), hr_span)

    # Light theme using 256 colours
    t = "light"
    THEMES[t, "category"] = "\033[38;5;160;1m"  # crimson red + bold
    THEMES[t, "target"] = "\033[38;5;33;1m"     # vivid medium blue + bold
    THEMES[t, "argument"] = "\033[38;5;214m"    # bright orange
    THEMES[t, "value"] = "\033[38;5;214;4m"     # bright orange + underline
    THEMES[t, "argument"] = "\033[38;5;130m"    # warm brown
    THEMES[t, "value"] = "\033[38;5;130;4m"     # warm brown + underline
    THEMES[t, "prologue"] = ""                  # Leave these or stuff breaks
    THEMES[t, "description"] = ""               # Leave these or stuff breaks
    THEMES[t, "warning"] = "\033[38;5;196;1;7m" # bright red + bold + reverse
    THEMES[t, "code"] = "\033[4;2m"             # dim+underline for code in backticks
    THEMES[t, "code-reset"] = "\033[24;22m"
    THEMES[t, "bold"] = "\033[1m"
    THEMES[t, "bold-reset"] = "\033[22m"
    THEMES[t, "italic"] = "\033[3m"
    THEMES[t, "italic-reset"] = "\033[23m"
    THEMES[t, "underline"] = "\033[4m"
    THEMES[t, "underline-reset"] = "\033[24m"
    THEMES[t, "reset"] = "\033[0m"
    hr_span = spaces(WIDTH - IN_L_HR - IN_R_HR)
    gsub(/ /, "q", hr_span)
    THEMES[t, "hr"] = sprintf("%s\033[38;5;246m\033(0%s\033(B\033[0m", spaces(IN_L_HR), hr_span)

    # Basic theme using 8 colour scheme
    t = "basic"
    THEMES[t, "category"] = "\033[31m"      # red
    THEMES[t, "target"] = "\033[36m"        # cyan
    THEMES[t, "argument"] = "\033[33m"      # yellow
    THEMES[t, "value"] = "\033[33;4m"       # yellow + underline
    THEMES[t, "prologue"] = ""
    THEMES[t, "description"] = ""
    THEMES[t, "warning"] = "\033[1;93;7m"
    THEMES[t, "code"] = "\033[4;2m"         # dim+underline for code in backticks
    THEMES[t, "code-reset"] = "\033[24;22m"
    THEMES[t, "bold"] = "\033[1m"
    THEMES[t, "bold-reset"] = "\033[22m"
    THEMES[t, "italic"] = "\033[3m"
    THEMES[t, "italic-reset"] = "\033[23m"
    THEMES[t, "underline"] = "\033[4m"
    THEMES[t, "underline-reset"] = "\033[24m"
    THEMES[t, "reset"] = "\033[0m"          # reset everything
    #  Won't work on some terminals (e.g macOS Terminal.app) but is benign.
    hr_span = spaces(WIDTH - IN_L_HR - IN_R_HR)
    gsub(/ /, "q", hr_span)
    THEMES[t, "hr"] = sprintf("%s\033[38;5;246m\033(0%s\033(B\033[0m", spaces(IN_L_HR), hr_span)

    # Light 8 colour theme
    t = "light8"
    THEMES[t, "category"] = "\033[35m"      # magenta
    THEMES[t, "target"] = "\033[32m"        # green
    THEMES[t, "argument"] = "\033[34m"      # blue
    THEMES[t, "value"] = "\033[34;4m"       # blue + underline
    THEMES[t, "prologue"] = ""
    THEMES[t, "description"] = ""
    THEMES[t, "warning"] = "\033[1;93;7m"
    THEMES[t, "code"] = "\033[4;2m"         # dim+underline for code in backticks
    THEMES[t, "code-reset"] = "\033[24;22m"
    THEMES[t, "bold"] = "\033[1m"
    THEMES[t, "bold-reset"] = "\033[22m"
    THEMES[t, "italic"] = "\033[3m"
    THEMES[t, "italic-reset"] = "\033[23m"
    THEMES[t, "underline"] = "\033[4m"
    THEMES[t, "underline-reset"] = "\033[24m"
    THEMES[t, "reset"] = "\033[0m"          # reset everything
    hr_span = spaces(WIDTH - IN_L_HR - IN_R_HR)
    gsub(/ /, "q", hr_span)
    THEMES[t, "hr"] = sprintf("%s\033[37;2;9m%s\033[0m", spaces(IN_L_HR), hr_span)

    # Dark 8 colour theme
    t = "dark8"
    THEMES[t, "category"] = "\033[91m"      # bright red
    THEMES[t, "target"] = "\033[96m"        # bright cyan
    THEMES[t, "argument"] = "\033[93m"      # bright yellow
    THEMES[t, "value"] = "\033[93;4m"       # bright yellow + underline
    THEMES[t, "prologue"] = ""
    THEMES[t, "description"] = ""
    THEMES[t, "warning"] = "\033[1;93;7m"
    THEMES[t, "code"] = "\033[4;2m"         # dim+underline for code in backticks
    THEMES[t, "code-reset"] = "\033[24;22m"
    THEMES[t, "bold"] = "\033[1m"
    THEMES[t, "bold-reset"] = "\033[22m"
    THEMES[t, "italic"] = "\033[3m"
    THEMES[t, "italic-reset"] = "\033[23m"
    THEMES[t, "underline"] = "\033[4m"
    THEMES[t, "underline-reset"] = "\033[24m"
    THEMES[t, "reset"] = "\033[0m"
    hr_span = spaces(WIDTH - IN_L_HR - IN_R_HR)
    gsub(/ /, "q", hr_span)
    THEMES[t, "hr"] = sprintf("%s\033[37;2m\033(0%s\033(B\033[0m", spaces(IN_L_HR), hr_span)

    # none theme
    t = "none"
    THEMES[t, "category"] = ""
    THEMES[t, "target"] = ""
    THEMES[t, "argument"] = ""
    THEMES[t, "value"] = ""
    THEMES[t, "prologue"] = ""
    THEMES[t, "description"] = ""
    THEMES[t, "warning"] = ""
    THEMES[t, "code"] = "`"
    THEMES[t, "code-reset"] = "`"
    THEMES[t, "bold"] = "++"    # Cannot be ** or will clash with italic
    THEMES[t, "bold-reset"] = "++"
    THEMES[t, "italic"] = "/"  # Need to avoid * to avoid clash with bold
    THEMES[t, "italic-reset"] = "/"
    THEMES[t, "underline"] = "_"
    THEMES[t, "underline-reset"] = "_"
    THEMES[t, "reset"] = ""
    hr_span = spaces(WIDTH - IN_L_HR - IN_R_HR)
    gsub(/ /, "-", hr_span)
    THEMES[t, "hr"] = spaces(IN_L_HR) hr_span

    # Set active theme
    if (!((theme, "category") in THEMES))
        theme = "dark"

    # Load active theme
    F_CAT = THEMES[theme, "category"]
    F_TGT = THEMES[theme, "target"]
    F_ARG = THEMES[theme, "argument"]
    F_VAL = THEMES[theme, "value"]
    F_LOG = THEMES[theme, "prologue"]       # Prologue and epilogue
    F_DSC = THEMES[theme, "description"]    # Target and variable descriptions
    F_WARN = THEMES[theme, "warning"]
    F_CODE = THEMES[theme, "code"]          # Code in backticks
    R_CODE = THEMES[theme, "code-reset"]
    F_BOLD = THEMES[theme, "bold"]
    R_BOLD = THEMES[theme, "bold-reset"]
    F_ITAL = THEMES[theme, "italic"]
    R_ITAL = THEMES[theme, "italic-reset"]
    F_UNDL = THEMES[theme, "underline"]
    R_UNDL = THEMES[theme, "underline-reset"]
    R_ALL = THEMES[theme, "reset"]
    HR = THEMES[theme, "hr"]
}

# Try to determine TTY width. Returns 0 on failure.
# WARNING: Do not use tput -- not safe if not running on tty.
function tty_columns(    cmd, a, line) {
    if (ENVIRON["COLUMNS"] > 0)
        return ENVIRON["COLUMNS"] + 0

    if ((cmd = "stty size < /dev/tty 2>/dev/null") | getline line) {
        close(cmd)
        split(line, a)
        if (a[2] > 0) return a[2] + 0
    }
    return 0
}

function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }

function strip_ansi(s) { gsub(/\033\[[0-9;]*m/, "", s); return s }

function spaces(n) { return sprintf("%" n "s", "") }

function join(s1, s2, sep) {
    if (s1 != "") return s2 == "" ? s1 : s1 sep s2
    return s2 == "" ? "" : s2
}

# Bubble sort for arrays (No gawk isort in POSIX awk)
# Keys are consecutive integers starting with 1
# Beware!! This is locale based sorting. You will be surprised.
function sort_array(arr, n,    i, j, tmp) {
    for (i = 1; i < n; i++)
        for (j = i + 1; j <= n; j++)
            if (arr[i] > arr[j]) {
                tmp = arr[i]
                arr[i] = arr[j]
                arr[j] = tmp
            }
}

# Filter entries from a multidimensional array where the first subscript
# matches `first_key`. Populates dest[first_sub, second_sub...] = value
function afilter(array, first_key, dest,    key, parts, subkey) {
    split("", dest)
    for (key in array) {
        split(key, parts, SUBSEP)
        if (parts[1] == first_key) {
            subkey = parts[2]
            dest[subkey] = array[key]
        }
    }
}

# Print a string to stderr
function stderr(s) { print s | "cat 1>&2"; close("cat 1>&2") }

function warning(s) { stderr(F_WARN "WARNING: " s R_ALL) }

function dprint(s) { if (!DEBUG) return; stderr("DEBUG: " s) }

# For debugging -- print array contents
function aprint(heading, array,    k, key) {
    stderr(heading ":")
    for (k in array) {
        key = k
        gsub(SUBSEP, ", ", key)
        stderr("    (" key ") = \"" array[k] "\"")
    }
    stderr("-----------")
}

# Unescape ANSI codes to reactivate them
function unescape(s,   i, j, c, o) {
    gsub(/\\033|\\x1b|\\e/, "\033", s)
    gsub(/\\a/, "\007", s)
    gsub(/\\b/, "\010", s)
    gsub(/\\f/, "\014", s)
    gsub(/\\n/, "\n", s)
    gsub(/\\r/, "\r", s)
    gsub(/\\t/, "\t", s)
    gsub(/\\v/, "\013", s)

    # octal \000 sequences (up to 3 digits)
    i = 1
    while (i <= length(s)) {
        if (substr(s, i, 1) == "\\" && match(substr(s, i + 1), "^[0-7]{1,3}")) {
            # extract matched octal digits
            o = substr(s, i + 1, RLENGTH)
            # convert octal manually
            c = 0
            for (j = 1; j <= length(o); j++) {
                c = c * 8 + int(substr(o, j, 1))
            }
            s = substr(s, 1, i - 1) sprintf("%c", c) substr(s, i + 1 + length(o))
            i += 0  # stay at this position in case multiple sequences
        } else {
            i++
        }
    }
    return s
}

# Expand Make style variable references $(VAR) and $x
# First checks target-specific vars, then falls back to global vars
function expand_vars(s, tgt,    pre, var, post, repl, r) {
    gsub(/\$\$/, "__DOLLAR__", s)  # Watch out for $$ escapes
    while (match(s, /\$\([A-Za-z0-9_]+\)|\$[A-Za-z0-9_@]/)) {
        pre = substr(s, 1, RSTART - 1)
        post = substr(s, RSTART + RLENGTH)
        r = substr(s, RSTART, RLENGTH)
        if (substr(r, 1, 2) == "$(")
            var = substr(r, 3, RLENGTH - 3)
        else
            var = substr(r, 2, 1)
        # Check target-specific first, then global
        if ((tgt, var) in TargetMakeVars)
            repl = TargetMakeVars[tgt, var]
        else if (var in GlobalMakeVars)
            repl = GlobalMakeVars[var]
        else
            repl = ""
        s = pre repl post
    }
    gsub(/__DOLLAR__/, "$", s)
    return s
}

# Add a token to the specified array for the given target.
# The token is either `name` or `name=value`.
function parse_arg(token, arr,    name, value, eq_pos) {
    eq_pos = index(token, "=")
    if (eq_pos) {
        name = substr(token, 1, eq_pos - 1)
        value = substr(token, eq_pos + 1)
    } else {
        name = token
        value = ""
    }
    arr[name] = value
}

# Add some simple markdown-like inline styling for bold, italic. underline, backtick
function style_inline(s,    pre, mid, post, new_s) {
    # Phase 1: shield escaped characters
    gsub(/\\\\/, "__ESC_BSLASH__", s)
    gsub(/\\\*/, "__ESC_STAR__", s)
    gsub(/\\_/, "__ESC_UNDER__", s)
    gsub(/\\`/, "__ESC_TICK__", s)

    # Phase 2: apply inline styles

    # Backticks: `code`
    while (match(s, /`[^`]+`/)) {
        pre = substr(s, 1, RSTART - 1)
        mid = substr(s, RSTART + 1, RLENGTH - 2)
        post = substr(s, RSTART + RLENGTH)
        new_s = pre F_CODE mid R_CODE post
        if (new_s == s) break
        s = new_s
    }

    # Bold: **text**
    while (match(s, /\*\*[^*]+\*\*/)) {
        pre = substr(s, 1, RSTART - 1)
        mid = substr(s, RSTART + 2, RLENGTH - 4)
        post = substr(s, RSTART + RLENGTH)
        new_s = pre F_BOLD mid R_BOLD post
        if (new_s == s) break
        s = new_s
    }

    # Italic: *text*
    while (match(s, /\*[^*]+\*/)) {
        pre = substr(s, 1, RSTART - 1)
        mid = substr(s, RSTART + 1, RLENGTH - 2)
        post = substr(s, RSTART + RLENGTH)
        new_s = pre F_ITAL mid R_ITAL post
        if (new_s == s) break
        s = new_s
    }

    # Underline: _text_
    while (match(s, /_[^_]+_/)) {
        pre = substr(s, 1, RSTART - 1)
        mid = substr(s, RSTART + 1, RLENGTH - 2)
        post = substr(s, RSTART + RLENGTH)
        new_s = pre F_UNDL mid R_UNDL post
        if (new_s == s) break
        s = new_s
    }

    # Phase 3: restore escaped characters
    gsub(/__ESC_BSLASH__/, "\\", s)
    gsub(/__ESC_STAR__/, "*", s)
    gsub(/__ESC_UNDER__/, "_", s)
    gsub(/__ESC_TICK__/, "`", s)

    return s
}

# Wrap lines of text with optional indenting. First line indent on the left can
# be different from subsequent lines. Handles non-nested ANSI inline styles
# correctly across wraps.
function wrap(text, first_indent, left_indent, right_indent, \
            available_width, n, i, w, line, test, active_style, word, indent_s) {

    indent_s = spaces(first_indent)
    available_width = WIDTH - first_indent - right_indent

    n = split(text, w, /[[:space:]]+/)
    line = ""
    active_style = ""

    for (i = 1; i <= n; i++) {
        word = w[i]
        test = join(line, word, " ")

        # Wrap before mutating style state
        if (length(strip_ansi(test)) > available_width) {
            # Terminate any active style on the output line
            if (active_style)
                printf "%s%s%s\n", indent_s, line, R_ALL
            else
                printf "%s%s\n", indent_s, line
            indent_s = spaces(left_indent)
            available_width = WIDTH - left_indent - right_indent

            # Start continuation line: reapply any active style after indent
            line = active_style ? active_style word : word
        } else {
            line = test
        }

        # Update style state based on END STATE of this word
        if (index(word, R_ALL)) active_style = ""
        else if (index(word, R_BOLD)) active_style = ""
        else if (index(word, R_ITAL)) active_style = ""
        else if (index(word, R_UNDL)) active_style = ""
        else if (index(word, R_CODE)) active_style = ""
        else if (index(word, F_BOLD)) active_style = F_BOLD
        else if (index(word, F_ITAL)) active_style = F_ITAL
        else if (index(word, F_UNDL)) active_style = F_UNDL
        else if (index(word, F_CODE)) active_style = F_CODE
    }

    if (line) {
        if (active_style)
            printf "%s%s%s\n", indent_s, line, R_ALL
        else
            printf "%s%s\n", indent_s, line
    }
}

# Print paragraphs from array with proper joining, wrapping, and automatic styling
# The tgt (target) provides context for var expansion. Set to "" for paragraphs
# that don't have a target context.
function print_paragraphs(tgt, arr, n, style, left_indent, right_indent,    i, raw, line, para) {

    para = ""
    for (i = 1; i <= n; i++) {
        raw = expand_vars(arr[i], tgt)
        if (raw ~ /^[[:space:]]*$/) {
            # Paragraph break: whitespace-only line
            if (para) {
                wrap(para, left_indent, left_indent, right_indent)
                para = ""
            }
            print ""
            continue
        }
        line = style style_inline(raw) R_ALL
        para = join(para, line, " ")
    }
    if (para)
        wrap(para, left_indent, left_indent, right_indent)
}

# Format either the required or optional args for a target into a string.
function format_args(arg_array, tgt, prefix, suffix, \
                    s, tmp_args, sorted_args, arg, val, arg_count, i) {

    afilter(arg_array, tgt, tmp_args)
    if (length(tmp_args) == 0) return

    arg_count = 0
    for (arg in tmp_args) sorted_args[++arg_count] = arg
    sort_array(sorted_args, arg_count)

    for (i = 1; i <= arg_count; i++) {
        arg = sorted_args[i]
        val = tmp_args[arg] != "" ? tmp_args[arg] : \
              ((tgt, arg) in TargetMakeVars ? TargetMakeVars[tgt, arg] : \
              (arg in GlobalMakeVars ? GlobalMakeVars[arg] : ""))
        s = s sprintf(" %s%s%s=%s%s%s%s%s%s%s", F_ARG, prefix, arg, R_ALL, F_VAL, val, R_ALL, F_ARG, suffix, R_ALL)
    }
    return s
}

# Recursive target argument resolver.
# Populates ResolvedReq[tgt, var] and ResolvedOpt[tgt, var]
function resolve_target(tgt, depth, visited, \
                        dep_list, n, i, dep, tmp_req, tmp_opt, var) {

    if (depth > DEPENDENCY_RECURSION_LIMIT || tgt in visited)
        return
    visited[tgt] = 1

    # First, resolve dependencies
    if (TargetDeps[tgt]) {
        n = split(TargetDeps[tgt], dep_list)
        for (i = 1; i <= n; i++) {
            dep = dep_list[i]
            if (dep == "") continue
            resolve_target(dep, depth + 1, visited)

            # Merge required args from dependency
            afilter(ResolvedReq, dep, tmp_req)
            for (var in tmp_req)
                ResolvedReq[tgt, var] = tmp_req[var]

            # Merge optional args from dependency
            afilter(ResolvedOpt, dep, tmp_opt)
            for (var in tmp_opt)
                ResolvedOpt[tgt, var] = tmp_opt[var]
        }
    }

    # Merge this target’s own required args
    afilter(TargetReqVars, tgt, tmp_req)
    for (var in tmp_req)
        ResolvedReq[tgt, var] = tmp_req[var]

    # Merge this target’s own optional args
    afilter(TargetOptVars, tgt, tmp_opt)
    for (var in tmp_opt)
        ResolvedOpt[tgt, var] = tmp_opt[var]
}

# ------------------------------------------------------------------------------
# Join continuation lines
# ------------------------------------------------------------------------------
{
    if (CurrentFile != FILENAME) {
        if (LineContinuation) {
            warning("File " CurrentFile " ends with a continuation")
            LineBuf = ""
            LineContinuation = 0
        }
        CurrentFile = FILENAME
    }
    if (LineContinuation) {
        sub(/[[:space:]]*\\[[:space:]]*$/, "", LineBuf)
        LineBuf = LineBuf " " trim($0)
    } else {
        LineBuf = $0
    }

    if (match($0, /[[:space:]]*\\[[:space:]]*$/)) {
        LineContinuation = 1
        next
    } else {
        LineContinuation = 0
        $0 = LineBuf
        LineBuf = ""
    }
}

# ------------------------------------------------------------------------------
# In preprocess mode, we are processng the output of "make -pn", looking for
# variable assignments so we can generate "#:var" and "#:tvar" directives for
# consumption in a later processing phase. This is basically a simple state
# machine. Note that macOS make is ancient (v3) and exposes target specific vars
# in a different way to make 4+. We handle both formats here.
# ------------------------------------------------------------------------------

NF == 0 { PreState = "" ; PreTarget = ""; next }
PRE && PreState == "not-target" { next }
PRE && /^# Not a target:/ { PreState = "not-target" ; PreTarget = "" ; next }

# Target specification
PRE && PreState == "" && /^[^:#[:space:]]+:/ && ! /[:?+!]*=/ {
        sub(/:.*/, "")
        PreTarget = $0
        PreState = "target"
        next
}

# make 3 (macOS) : Target specific variables : # var = value
PRE && PreState == "target" && /^#[[:space:]]*[^:[:space:]]+[[:space:]]+:*=/ {
    sub(/^#[[:space:]]*/, "")
    pos = match($0, /[[:space:]]*:*=[[:space:]]*/)
    val = substr($0, pos + RLENGTH)
    printf "#:tvar %s %s=%s\n", PreTarget, substr($0, 1, pos - 1), val
    next
}

# make 4 (rest of universe): Target specific variables : target: var = value
# We deliberately ignore conditional and append assignments.
PRE && /^[^:#[:space:]]+:.*[:?+!]*=/ {
    # Extract target name
    tgt = $0
    sub(/:.*/, "", tgt)
    # Extract the assignment part
    sub(/^[^:#[:space:]]+:[[:space:]]*/, "")
    pos = match($0, /[[:space:]]*:*=[[:space:]]*/)
    val = substr($0, pos + RLENGTH)
    printf "#:tvar %s %s=%s\n", tgt, substr($0, 1, pos - 1), val
    next
}

# Variable assignment
PRE && PreState == "" && /^[[:space:]]*[A-Za-z0-9_.-][A-Za-z0-9_.-]*[[:space:]]*[:+!?]*=/ {
    pos = match($0, /[[:space:]]*[:+!?]*=[[:space:]]*/)
    printf "#:var %s=%s\n", substr($0, 1, pos - 1), substr($0, pos + RLENGTH)
}

PRE { next }

# ------------------------------------------------------------------------------
# Directive handlers. Directives are injected via Makefile comments.
# ------------------------------------------------------------------------------

# Pre-resolved Make global variables: #:var NAME=VALUE
# Most of these come from output of `make -pn`.
$1 == "#:var" {
    sub(/^[^[:space:]]+[[:space:]]*/, "")  # Remove $1
    pos = index($0, "=")
    name = substr($0, 1, pos - 1)
    value = substr($0, pos + 1)
    GlobalMakeVars[name] = unescape(value)
    next
}

# Pre-resolved Make target specific variables: #:tvar TARGET NAME=VALUE
# Most of these come from output of `make -pn`.
$1 == "#:tvar" {
    tgt = $2
    sub(/^[^[:space:]]+[[:space:]]*/, "")  # Remove $1
    sub(/^[^[:space:]]+[[:space:]]*/, "")  # Remove $2
    pos = index($0, "=")
    name = substr($0, 1, pos - 1)
    value = substr($0, pos + 1)
    TargetMakeVars[tgt, name] = value
}

$1 == "#:" {
    warning(FILENAME ": Line " FNR " has a bare #: -- could be a directive typo")
    next
}

# Category for makefile target : #:cat Title
$1 == "#:cat" {
    sub(/^[^[:space:]]+[[:space:]]*/, "")  # Remove $1
    TargetCategory = trim($0)
    # Keep track of ordering of category list
    if (!(TargetCategory in TargetCategoryIndex))
        TargetCategoryIndex[TargetCategory] = length(TargetCategoryIndex) + 1
    next
}

# Category for makefile variable : #:vcat Title
$1 == "#:vcat" {
    sub(/^[^[:space:]]+[[:space:]]*/, "")  # Remove $1
    VarCategory = trim($0)
    # Keep track of ordering of category list
    if (!(VarCategory in VarCategoryIndex))
        VarCategoryIndex[VarCategory] = length(VarCategoryIndex) + 1
    next
}

# Required argument(s) : #:req
$1 == "#:req" {
    for (i = 2; i <= NF; i++)
        parse_arg($i, PendingReq)
    next
}

# Optional argument(s) : #:opt
$1 == "#:opt" {
    for (i = 2; i <= NF; i++)
        parse_arg($i, PendingOpt)
    next
}

# Target documentation.
$1 == "##" {
    line = trim(substr($0, 3))
    doc_lines[++doc_count] = line
    next
}

# Prologue line
$1 == "#+" {
    line = trim(substr($0, 3))
    prologue_text[++PrologueCount] = line
    next
}

# Epilogue line
$1 == "#-" {
    line = trim(substr($0, 3))
    epilogue_text[++EpilogueCount] = line
    next
}

# Skip simple comments
/^#[^#:+-]/ { next }
/^#[[:space:]]*$/ { next }

# ------------------------------------------------------------------------------
# Target detection.
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Target detection.
# ------------------------------------------------------------------------------

/^[^#[:space:]].*:/ {
    if ($0 ~ /[:?+!]*=/) {
        ;         # Pass variable assignments to next pattern
    } else {
        # Parse and store dependencies if resolution is enabled
        if (DEPENDENCY_RESOLUTION == "yes") {
            deps_part = $0
            sub(/[^:]*::?[[:space:]]*/, " ", deps_part)  # Single and double colon targets
            deps_part = trim(expand_vars(deps_part, "")) # These lines are not target sensitive
        } else
            deps_part = ""

        n_tgts = split(trim(expand_vars(substr($0, 1, index($0, ":") - 1), "")), tgts)
        for (n = 1; n <= n_tgts; n++) {
            tgt = tgts[n]

            # If we've already categorized this target, use that category
            cat = ""
            for (c in TargetCategoryIndex) {
                if ((c, tgt) in DescriptionCount) {
                    cat = c
                    break
                }
            }

            # First time with documentation - determine category
            if (cat == "") {
                # The "help" target is handled specially because user can't add #:cat for it.
                if (tgt == "help") {
                    if (tolower(HELP_CATEGORY) == "none") next
                    cat = HELP_CATEGORY
                } else
                    cat = (TargetCategory) ? TargetCategory : DEFAULT_CATEGORY
            }

            # Only add to category if this occurrence has documentation
            if (doc_count > 0) {
                # Keep track of ordering of category list
                if (!(cat in TargetCategoryIndex))
                    TargetCategoryIndex[cat] = length(TargetCategoryIndex) + 1

                # Track that we've seen this target in this category (but only add to list once)
                if (!((cat, tgt) in DescriptionCount)) {
                    TargetListByCat[cat, ++TargetCount[cat]] = tgt
                    DescriptionCount[cat, tgt] = 0
                }

                # Accumulate documentation
                for (i = 1; i <= doc_count; i++) {
                    Descriptions[cat, tgt, i + DescriptionCount[cat, tgt]] = doc_lines[i]
                }
                DescriptionCount[cat, tgt] += doc_count
            }

            TargetDeps[tgt] = join(TargetDeps[tgt], deps_part, " ")
            for (v in PendingReq)
                TargetReqVars[tgt, v] = expand_vars(PendingReq[v], tgt)
            for (v in PendingOpt)
                TargetOptVars[tgt, v] = expand_vars(PendingOpt[v], tgt)
        }
        # reset for next target
        doc_count = 0; RequiredArgs = ""; OptionalArgs = ""
        split("", PendingReq) ; split("", PendingOpt)
    }
}

# ------------------------------------------------------------------------------
# Variable description detection
#   Lines immediately before assignment are ## comments
#   $0 = NAME=VALUE
#   Note that we need to handle the various forms of make assignment (:= etc).
# ------------------------------------------------------------------------------

$1 == "override" {
    sub(/^[^[:space:]]+[[:space:]]*/, "")  # Remove $1
}

/^[A-Za-z0-9_]+[[:space:]]*[:+!?]*=/ {
    if (doc_count == 0) { doc_count = 0; next }

    split($0, a, /[:+!?]*=/)
    name = trim(a[1])
    GlobalMakeVars[name] = (name in GlobalMakeVars) ? GlobalMakeVars[name] : trim(a[2])

    # Keep track of ordering of category list
    if (!(VarCategory in VarCategoryIndex))
        VarCategoryIndex[VarCategory] = length(VarCategoryIndex) + 1

    vars_list[VarCategory, ++var_count[VarCategory]] = name
    VarDescriptionCount[VarCategory, name] = doc_count
    for (i = 1; i <= doc_count; i++)
        VarDescriptions[VarCategory, name, i] = doc_lines[i]

    # Reset for next var
    doc_count = 0
    next
}

# ------------------------------------------------------------------------------
# END block: output everything
# ------------------------------------------------------------------------------

END {
    if (LineContinuation)
        warning("File " CurrentFile " ends with a continuation")

    if (PRE) {
        if (LineBuf != "") print LineBuf
        exit(0)
    }

    # Debug output only
    if (DEBUG >= 2) aprint("GlobalMakeVars", GlobalMakeVars)
    if (DEBUG) aprint("TargetMakeVars", TargetMakeVars)

    # Step 1: Resolve and consolidate args for each target ---
    for (cat in TargetCount) {
        n = TargetCount[cat] + 0  # Busybox needs + 0
        for (i = 1; i <= n; i++) {
            tgt = TargetListByCat[cat, i]

            split("", visited)
            resolve_target(tgt, 0, visited)

            # Delete optionals overridden by required
            for (var in ResolvedOpt) {
                # Check only entries for this target
                split(var, parts, SUBSEP)
                if (parts[1] == tgt && (tgt SUBSEP parts[2]) in ResolvedReq)
                    delete ResolvedOpt[var]
            }
        }
    }

    # Step 2: Print the prologue.
    print ""
    if (PrologueCount) {
        print_paragraphs("", prologue_text, PrologueCount, F_LOG, IN_L_LOG, IN_R_LOG)
        print HR
        if (HR) print ""
    }

    # Step 3: Sort category list.
    if (sort_mode == "alpha") {
        cat_count = 0
        for (cat in TargetCount)
            sorted_cat_list[++cat_count] = cat
        sort_array(sorted_cat_list, cat_count)
    } else {
        cat_count = length(TargetCategoryIndex)
        for (cat in TargetCategoryIndex)
            sorted_cat_list[TargetCategoryIndex[cat]] = cat
    }

    # Step 4: Print target categories and targets.
    cat_indent_s = spaces(IN_L_CAT)
    for (ci = 1; ci <= length(sorted_cat_list); ci++) {
        cat = sorted_cat_list[ci]
        if (cat == "") continue  # BusyBox awk needs this. Mawk and gawk don't. Odd
        n = TargetCount[cat] + 0  # BusyBox awk needs this
        if (n == 0) continue
        printf "%s%s%s%s\n", cat_indent_s, F_CAT, cat, R_ALL

        for (i = 1; i <= n; i++)
            sorted_target_list[i] = TargetListByCat[cat, i]
        sort_array(sorted_target_list, n)

        for (i = 1; i <= n; i++) {
            tgt = sorted_target_list[i]
            if (DescriptionCount[cat, tgt] == 0) continue
            line = sprintf("%s%s%s", F_TGT, tgt, R_ALL) \
                format_args(ResolvedReq, tgt, "", "") \
                format_args(ResolvedOpt, tgt, "[", "]")
            wrap(line, IN_L_TGT, IN_L_TGT + length(tgt) + 1, 0)
            if (DescriptionCount[cat, tgt]) {
                for (j = 1; j <= DescriptionCount[cat, tgt]; j++)
                    para_lines[j] = Descriptions[cat, tgt, j]
                print_paragraphs(tgt, para_lines, DescriptionCount[cat, tgt], F_DSC, IN_L_DSC, IN_R_DSC)
            }
        }
        print ""
    }

    # Step 5: Sort the var category list.
    if (sort_mode == "alpha") {
        vcat_count = 0
        for (vcat in var_count) vcat_list[++vcat_count] = vcat
        sort_array(vcat_list, vcat_count)
    } else {
        vcat_count = length(VarCategoryIndex)
        for (vcat in VarCategoryIndex) vcat_list[VarCategoryIndex[vcat]] = vcat
    }

    # Step 6: Print var categories and vars.
    for (ci = 1; ci <= length(vcat_list); ci++) {
        vcat = vcat_list[ci]
        if (vcat == "") continue  # BusyBox awk needs this. Mawk and gawk don't. Odd
        n = var_count[vcat] + 0  # BusyBOx needs +0
        if (n == 0) continue
        printf "%s%s%s%s\n", cat_indent_s, F_CAT, vcat, R_ALL

        for (i = 1; i <= n; i++) vlist[i] = vars_list[vcat, i]
        sort_array(vlist, n)

        var_indent_s = spaces(IN_L_TGT)
        for (i = 1; i <= n; i++) {
            v = vlist[i]
            val = (v in GlobalMakeVars) ? GlobalMakeVars[v] : DEFAULT_VALUE
            printf "%s%s%s%s=%s%s%s\n", var_indent_s, F_ARG, v, R_ALL, F_VAL, val, R_ALL

            delete para_lines
            if (VarDescriptionCount[vcat, v]) {
                for (j = 1; j <= VarDescriptionCount[vcat, v]; j++)
                    para_lines[j] = VarDescriptions[vcat, v, j]
                print_paragraphs("", para_lines, VarDescriptionCount[vcat, v], F_DSC, IN_L_DSC, IN_R_DSC)
            }
        }
        print ""
    }

    # Step 7: Print the epilogue.
    if (EpilogueCount > 0 && HR) print HR
    print_paragraphs("", epilogue_text, EpilogueCount, F_LOG, IN_L_LOG, IN_R_LOG)
    print ""
}
