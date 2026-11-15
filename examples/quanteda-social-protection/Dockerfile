FROM rocker/r-ver@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c

RUN apt-get update \
    && apt-get install -y --no-install-recommends libicu-dev libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN install2.r --error --skipinstalled \
      fastmatch lifecycle magrittr Matrix Rcpp SnowballC stopwords stringi xml2 yaml \
    && Rscript -e 'install.packages("https://cloud.r-project.org/src/contrib/jsonlite_2.0.0.tar.gz", repos = NULL, type = "source")' \
    && Rscript -e 'install.packages("https://cloud.r-project.org/src/contrib/quanteda_4.5.0.tar.gz", repos = NULL, type = "source")' \
    && Rscript -e 'stopifnot(as.character(packageVersion("quanteda")) == "4.5.0", as.character(packageVersion("jsonlite")) == "2.0.0")'
