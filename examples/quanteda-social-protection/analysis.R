#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
  library(quanteda)
})

fail <- function(message) stop(message, call. = FALSE)
canonical_json <- function(value) toJSON(value, auto_unbox = TRUE, null = "null", na = "null", digits = NA)
read_json <- function(path) fromJSON(path, simplifyVector = FALSE)
write_json <- function(value, path) writeLines(paste0(canonical_json(value), "\n"), path, useBytes = TRUE)

runtime <- function() list(
  r = paste(R.version$major, R.version$minor, sep = "."),
  quanteda = as.character(packageVersion("quanteda")),
  jsonlite = as.character(packageVersion("jsonlite"))
)

segment <- function(input_path, output_path) {
  source <- read_json(input_path)
  if (!identical(source$language, "en")) fail("this example accepts English input only")
  units <- list()
  for (document in source$documents) {
    sentences <- as.list(as.character(tokens(document$text, what = "sentence")[[1]]))
    if (length(sentences) == 0) fail(paste("document has no sentence units:", document$id))
    for (index in seq_along(sentences)) {
      units[[length(units) + 1]] <- list(
        unitId = sprintf("%s:u%02d", document$id, index),
        documentId = document$id,
        documentTitle = document$title,
        ordinal = index - 1,
        text = sentences[[index]]
      )
    }
  }
  write_json(list(
    recordType = "segmentedSource",
    formatVersion = 1,
    datasetId = source$datasetId,
    language = source$language,
    topic = source$topic,
    selectionRule = source$selectionRule,
    license = source$license,
    documents = source$documents,
    units = units,
    segmentation = "quanteda::tokens(x, what = 'sentence'); order preserved per document",
    runtime = runtime()
  ), output_path)
}

matched_terms <- function(one_tokens, terms) {
  Filter(function(term) {
    selected <- tokens_select(one_tokens, pattern = phrase(term), selection = "keep",
                              valuetype = "fixed", case_insensitive = TRUE)
    ntoken(selected)[[1]] > 0
  }, terms)
}

analyze <- function(source_path, rules_path, output_path) {
  source_records <- read_json(source_path)
  rules <- read_json(rules_path)
  units <- source_records$units
  if (length(units) == 0) fail("AxolDB source contains no units")
  unit_ids <- vapply(units, `[[`, "", "unitId")
  texts <- vapply(units, `[[`, "", "text")
  names(texts) <- unit_ids
  word_tokens <- tokens(texts, what = "word", remove_punct = TRUE,
                        remove_numbers = TRUE, remove_symbols = TRUE)
  word_tokens <- tokens_tolower(word_tokens)
  analyses <- list()
  for (rule in rules) {
    terms <- unlist(rule$terms, use.names = FALSE)
    dictionary <- dictionary(list(social_protection = terms))
    hits <- tokens_lookup(word_tokens, dictionary = dictionary, valuetype = "fixed",
                          case_insensitive = TRUE, exclusive = TRUE)
    labels <- ntoken(hits) > 0
    unit_results <- vector("list", length(units))
    for (index in seq_along(units)) {
      exact_matches <- unname(unlist(matched_terms(word_tokens[index], terms), use.names = FALSE))
      unit_results[[index]] <- list(
        unitId = units[[index]]$unitId,
        documentId = units[[index]]$documentId,
        documentTitle = units[[index]]$documentTitle,
        unitOrdinal = units[[index]]$ordinal,
        text = units[[index]]$text,
        label = if (labels[[index]]) rule$label else "none",
        matchedExpressions = exact_matches
      )
    }
    document_ids <- unique(vapply(units, `[[`, "", "documentId"))
    aggregates <- lapply(document_ids, function(document_id) {
      selected <- Filter(function(row) identical(row$documentId, document_id), unit_results)
      count <- sum(vapply(selected, function(row) identical(row$label, rule$label), FALSE))
      list(
        documentId = document_id,
        documentTitle = selected[[1]]$documentTitle,
        denominatorSentenceUnits = length(selected),
        labeledSentenceUnits = count,
        labeledShare = count / length(selected)
      )
    })
    analyses[[length(analyses) + 1]] <- list(
      recordType = "dictionaryAnalysisResult",
      formatVersion = 1,
      datasetId = source_records$datasetId,
      dictionaryId = rule$dictionaryId,
      dictionaryVersion = rule$version,
      dictionaryStatus = rule$status,
      label = rule$label,
      matching = rule$matching,
      analysisUnit = "sentence",
      denominator = "number of quanteda sentence units in each document",
      runtime = runtime(),
      units = unit_results,
      documents = aggregates
    )
  }
  write_json(list(recordType = "analysisSet", formatVersion = 1,
                  datasetId = source_records$datasetId, analyses = analyses), output_path)
}

html_escape <- function(value) {
  value <- gsub("&", "&amp;", as.character(value), fixed = TRUE)
  value <- gsub("<", "&lt;", value, fixed = TRUE)
  value <- gsub(">", "&gt;", value, fixed = TRUE)
  value <- gsub('"', "&quot;", value, fixed = TRUE)
  gsub("'", "&#39;", value, fixed = TRUE)
}

render <- function(results_path, comparison_path, output_path) {
  results <- read_json(results_path)$analyses
  comparison <- read_json(comparison_path)
  narrow <- results[[1]]
  expanded <- results[[2]]
  widths <- 620
  bars <- character()
  labels <- character()
  for (index in seq_along(narrow$documents)) {
    y <- 26 + (index - 1) * 42
    old_width <- as.numeric(narrow$documents[[index]]$labeledShare) * widths
    new_width <- as.numeric(expanded$documents[[index]]$labeledShare) * widths
    bars <- c(bars,
      sprintf('<rect x="0" y="%d" width="%.2f" height="13" fill="#3569a8"/>', y, old_width),
      sprintf('<rect x="0" y="%d" width="%.2f" height="13" fill="#db7c26"/>', y + 14, new_width))
    labels <- c(labels, sprintf('<text x="630" y="%d">%s</text>', y + 12,
      html_escape(narrow$documents[[index]]$documentTitle)))
  }
  changed_rows <- vapply(comparison$changedUnits, function(row) sprintf(
    "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>",
    html_escape(row$unitId), html_escape(row$documentTitle), html_escape(row$text),
    html_escape(row$oldLabel), html_escape(row$newLabel),
    html_escape(paste(unlist(row$newMatchedExpressions), collapse = ", "))), "")
  share_rows <- vapply(seq_along(narrow$documents), function(index) sprintf(
    "<tr><td>%s</td><td>%d/%d (%.1f%%)</td><td>%d/%d (%.1f%%)</td></tr>",
    html_escape(narrow$documents[[index]]$documentTitle),
    narrow$documents[[index]]$labeledSentenceUnits, narrow$documents[[index]]$denominatorSentenceUnits,
    100 * narrow$documents[[index]]$labeledShare,
    expanded$documents[[index]]$labeledSentenceUnits, expanded$documents[[index]]$denominatorSentenceUnits,
    100 * expanded$documents[[index]]$labeledShare), "")
  html <- c(
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Quanteda dictionary comparison</title>",
    "<style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18212b}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd5df;padding:.55rem;text-align:left;vertical-align:top}th{background:#eef3f7}.note{background:#fff4d6;padding:1rem}svg{max-width:100%;height:auto}code{background:#eef3f7;padding:.1rem .3rem}</style></head><body>",
    "<h1>How much does a dictionary change the result?</h1>",
    sprintf("<p class=\"note\">Illustrative fixed dictionaries, not a validated sociological instrument. A match is not evidence of a political position. Analysis unit: sentence; denominator: sentence units per document. Reloaded and recomputed from AxolDB: <strong>%s</strong>.</p>", if (comparison$checks$exactRecomputeMatch) "yes" else "no"),
    sprintf("<p><code>%s %s</code> compared with <code>%s %s</code>. R %s; quanteda %s.</p>",
      html_escape(narrow$dictionaryId), html_escape(narrow$dictionaryVersion),
      html_escape(expanded$dictionaryId), html_escape(expanded$dictionaryVersion),
      html_escape(narrow$runtime$r), html_escape(narrow$runtime$quanteda)),
    "<h2>Share of labeled sentence units</h2><p><span style=\"color:#3569a8\">■ narrow</span> &nbsp; <span style=\"color:#db7c26\">■ expanded</span></p>",
    sprintf('<svg viewBox="0 0 1100 %d" role="img" aria-label="Grouped bars of labeled sentence shares"><line x1="0" y1="12" x2="620" y2="12" stroke="#8895a3"/>%s%s</svg>', 50 + length(narrow$documents) * 42, paste(bars, collapse=""), paste(labels, collapse="")),
    "<table><thead><tr><th>Document</th><th>Narrow</th><th>Expanded</th></tr></thead><tbody>", paste(share_rows, collapse=""), "</tbody></table>",
    sprintf("<h2>Changed units (%d)</h2>", length(comparison$changedUnits)),
    "<table><thead><tr><th>Unit ID</th><th>Document</th><th>Text</th><th>Old</th><th>New</th><th>Expanded matches</th></tr></thead><tbody>", paste(changed_rows, collapse=""), "</tbody></table>",
    "<p>Source: GOV.UK snapshots. Contains public sector information licensed under the Open Government Licence v3.0.</p>",
    "</body></html>"
  )
  writeLines(paste(html, collapse = "\n"), output_path, useBytes = TRUE)
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) fail("usage: analysis.R segment|analyze|render ...")
if (args[[1]] == "segment" && length(args) == 3) {
  segment(args[[2]], args[[3]])
} else if (args[[1]] == "analyze" && length(args) == 4) {
  analyze(args[[2]], args[[3]], args[[4]])
} else if (args[[1]] == "render" && length(args) == 4) {
  render(args[[2]], args[[3]], args[[4]])
} else {
  fail("invalid analysis.R arguments")
}
