Quickstart:

  vsearch index path-to-data

  vsearch search path-to-data "query string"

By default, vsearch gives you the chunks that matched your query.  Use grep-inspired options to change this to give filesnames:

  vsearch search -l path-to-data "query string"
