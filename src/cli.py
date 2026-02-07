"""Command-line interface for the data curation tool."""

import click
from pathlib import Path
import pandas as pd
import sys
import os
from .config import Config
from .ingestion import DataIngestionManager
from .cleaning import DataCleaner

try:
    from .metadata import MetadataGenerator
except Exception:
    MetadataGenerator = None
from .searcher import IndicatorSearcher
from .dataset_catalog import DatasetCatalog

# Fix Windows encoding for Unicode output
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Mises Data Curation Tool - Automate economic data curation workflows."""
    pass


@cli.command()
@click.option("--config", default="config.yaml", help="Path to configuration file")
def init(config):
    """Initialize directory structure for data curation."""
    click.echo("🚀 Initializing Mises Data Curation Tool...")

    try:
        cfg = Config(config)
        cfg.initialize_directories()
        click.echo("✅ Directory structure created successfully!")
        click.echo("\nNext steps:")
        click.echo("1. Copy .env.example to .env and add your API keys")
        click.echo("2. Use 'curate ingest' to import data")
        click.echo("3. Use 'curate clean' to process datasets")
        click.echo("4. Use 'curate document' to generate metadata")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("query", required=False)
@click.option("--tag", help="Search by specific tag (e.g., wages, fiscal, inequality)")
@click.option(
    "--source",
    type=click.Choice(["owid", "ilostat", "oecd", "imf", "worldbank", "eclac"]),
    help="Filter by source",
)
@click.option("--list-topics", is_flag=True, help="List all available topics")
@click.option("--list-sources", is_flag=True, help="List all available sources")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def search(query, tag, source, list_topics, list_sources, verbose, config):
    """Search for available economic indicators (like 'apt search')."""
    try:
        cfg = Config(config)
        searcher = IndicatorSearcher(cfg)

        # List all tags
        if list_topics:
            tags = searcher.list_tags()
            click.echo("🏷️  Available Tags:\n")
            # Group tags in columns
            for i in range(0, len(tags), 4):
                row = tags[i : i + 4]
                click.echo("  " + "  ".join(f"{tag:<20}" for tag in row))
            return

        # List all sources
        if list_sources:
            sources = searcher.list_sources()
            click.echo("🌐 Available Sources:\n")
            for s in sources:
                indicators = searcher.search_by_source(s)
                click.echo(f"  {s.upper():<15} ({len(indicators)} indicators)")
            return

        # Search by source
        if source:
            results = searcher.search_by_source(source)
            click.echo(f"\n🔍 Indicators from {source.upper()}:\n")
            click.echo(searcher.format_results_table(results, verbose=verbose))
            return

        # Search by tag
        if tag:
            results = searcher.search_by_tag(tag)
            click.echo(f"\n🔍 Indicators with tag: {tag}\n")
            click.echo(searcher.format_results_table(results, verbose=verbose))
            return

        # General search
        if not query:
            click.echo("Usage: curate search <query> [OPTIONS]")
            click.echo("\nExamples:")
            click.echo(
                "  curate search wage              # Search for wage-related indicators"
            )
            click.echo("  curate search --list-topics     # See all available tags")
            click.echo("  curate search --source owid     # See OWID indicators")
            click.echo("  curate search --tag wages       # Search by specific tag")
            click.echo("  curate search informal -v       # Detailed search results")
            return

        results = searcher.search(query)

        if results:
            click.echo(f"\n🔍 Search results for '{query}':\n")
            click.echo(searcher.format_results_table(results, verbose=verbose))

            if not verbose:
                click.echo("\nUse -v for more details, or:")
                if results:
                    first = results[0]["name"]
                    click.echo(f"  curate search {first} -v")
        else:
            click.echo(f"❌ No results found for '{query}'")
            click.echo("\nTry:")
            click.echo("  curate search --list-topics  # See available topics")
            click.echo("  curate search --list-sources # See available sources")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--source",
    type=click.Choice(
        ["manual", "owid", "ilostat", "oecd", "imf", "worldbank", "eclac"]
    ),
    required=True,
    help="Data source",
)
@click.option(
    "--filepath", type=click.Path(exists=True), help="Path to file (for manual uploads)"
)
@click.option("--indicator", help="Indicator name or code")
@click.option("--dataset", help="Dataset identifier (for OECD)")
@click.option("--database", help="Database identifier (for IMF)")
@click.option("--countries", help="Country codes (comma-separated, e.g., ARG,BRA,CHL)")
@click.option("--start-year", type=int, default=2010, help="Starting year")
@click.option("--end-year", type=int, default=2024, help="Ending year")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def ingest(
    source,
    filepath,
    indicator,
    dataset,
    database,
    countries,
    start_year,
    end_year,
    config,
):
    """Ingest data from various sources (manual upload or public APIs)."""
    click.echo(f"📥 Ingesting data from {source.upper()}...")

    try:
        cfg = Config(config)
        manager = DataIngestionManager(cfg)

        # Parse countries list
        country_list = None
        if countries:
            country_list = [c.strip().upper() for c in countries.split(",")]

        # Build kwargs based on source
        kwargs = {"start_year": start_year, "end_year": end_year}

        if country_list:
            kwargs["countries"] = country_list

        if source == "manual":
            if not filepath:
                raise click.UsageError("--filepath is required for manual uploads")
            kwargs["filepath"] = filepath
        elif source == "ilostat":
            if not indicator:
                raise click.UsageError("--indicator is required for ILOSTAT")
            kwargs["indicator"] = indicator
        elif source == "oecd":
            if not dataset:
                raise click.UsageError("--dataset is required for OECD")
            kwargs["dataset"] = dataset
            if indicator:
                kwargs["indicator"] = indicator
        elif source == "imf":
            if not database or not indicator:
                raise click.UsageError(
                    "--database and --indicator are required for IMF"
                )
            kwargs["database"] = database
            kwargs["indicator"] = indicator

        # Ingest data
        data = manager.ingest(source, **kwargs)

        if len(data) == 0:
            click.echo("⚠ No data returned from source")
            click.echo("  Check your parameters and try again")
            return

        click.echo(f"✅ Ingested {len(data)} rows, {len(data.columns)} columns")
        click.echo(f"\nPreview (first 5 rows):")
        click.echo(data.head().to_string())

    except click.UsageError:
        raise
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["owid", "ilostat", "oecd", "imf", "worldbank", "eclac"]),
    required=True,
    help="Data source (API)",
)
@click.option("--slug", help="OWID chart slug (for owid source, e.g., real-wages)")
@click.option("--indicator", help="Indicator name or code")
@click.option("--dataset", help="Dataset identifier (for OECD)")
@click.option("--database", help="Database identifier (for IMF)")
@click.option(
    "--countries",
    help="Country names or codes (comma-separated, e.g., Argentina,Brazil,Chile)",
)
@click.option("--start-year", type=int, default=2010, help="Starting year")
@click.option("--end-year", type=int, default=2024, help="Ending year")
@click.option(
    "--topic", required=True, help="Topic for organization (e.g., salarios_reales)"
)
@click.option("--coverage", default="latam", help="Geographic coverage")
@click.option("--url", help="Original source URL for metadata")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def download(
    source,
    slug,
    indicator,
    dataset,
    database,
    countries,
    start_year,
    end_year,
    topic,
    coverage,
    url,
    config,
):
    """Download from API and pipeline in one step (ingest → clean → document)."""
    click.echo(f"🚀 Download + Pipeline: {source.upper()} → {topic}\n")

    try:
        cfg = Config(config)
        manager = DataIngestionManager(cfg)
        cleaner = DataCleaner(cfg)
        metadata_gen = MetadataGenerator(cfg)

        # Parse countries list
        country_list = None
        if countries:
            country_list = [c.strip() for c in countries.split(",")]

        # Step 1: DOWNLOAD from API
        click.echo(f"Step 1/3: Downloading from {source.upper()}...")

        kwargs = {"start_year": start_year, "end_year": end_year}

        if country_list:
            kwargs["countries"] = country_list

        if source == "owid":
            if not slug:
                raise click.UsageError(
                    "--slug is required for OWID (e.g., real-wages, gdp-per-capita)"
                )
            kwargs["slug"] = slug
        elif source == "ilostat":
            if not indicator:
                raise click.UsageError("--indicator is required for ILOSTAT")
            kwargs["indicator"] = indicator
        elif source == "oecd":
            if not dataset:
                raise click.UsageError("--dataset is required for OECD")
            kwargs["dataset"] = dataset
            if indicator:
                kwargs["indicator"] = indicator
        elif source == "imf":
            if not database or not indicator:
                raise click.UsageError(
                    "--database and --indicator are required for IMF"
                )
            kwargs["database"] = database
            kwargs["indicator"] = indicator
        elif source == "worldbank":
            if not indicator:
                raise click.UsageError("--indicator is required for World Bank")
            kwargs["indicator"] = indicator
        elif source == "eclac":
            if not indicator:
                raise click.UsageError(
                    "--indicator is required for ECLAC (use as table parameter)"
                )
            kwargs["table"] = indicator

        data = manager.ingest(source, **kwargs)

        if len(data) == 0:
            click.echo("⚠ No data returned from API")
            click.echo("  Check your parameters and try again")
            return

        click.echo(f"✓ Downloaded {len(data)} rows")

        # Step 2: CLEAN
        click.echo(f"\nStep 2/3: Cleaning data...")
        cleaned = cleaner.clean_dataset(data)
        output_path = cleaner.save_clean_dataset(
            cleaned, topic, source, coverage, start_year, end_year
        )
        transformations = cleaner.get_transformations()

        # Step 3: DOCUMENT
        click.echo(f"\nStep 3/3: Generating metadata...")
        data_summary = cleaner.get_data_summary(cleaned)
        metadata_content = metadata_gen.generate_metadata(
            topic=topic,
            data_summary=data_summary,
            source=source,
            transformations=transformations,
            original_source_url=url or f"https://{source}.org",
        )
        metadata_path = metadata_gen.save_metadata(topic, metadata_content)

        click.echo(f"\n✅ Complete! All in one command:\n")
        click.echo(f"   📥 Downloaded: {len(data)} rows from {source.upper()}")
        click.echo(f"   🧹 Cleaned: {len(cleaned)} rows")
        click.echo(f"   📊 Saved: {output_path}")
        click.echo(f"   📝 Documented: {metadata_path}")

    except click.UsageError:
        raise
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--topic", required=True, help="Topic name (e.g., salarios_reales)")
@click.option("--source", required=True, help="Source identifier (e.g., owid, ilostat)")
@click.option("--coverage", default="global", help="Geographic coverage")
@click.option(
    "--start-year", type=int, help="Starting year (auto-detected if not provided)"
)
@click.option(
    "--end-year", type=int, help="Ending year (auto-detected if not provided)"
)
@click.option("--config", default="config.yaml", help="Path to configuration file")
def clean(input_file, topic, source, coverage, start_year, end_year, config):
    """Clean and standardize a dataset."""
    click.echo(f"🧹 Cleaning dataset: {input_file}...")

    try:
        cfg = Config(config)
        cleaner = DataCleaner(cfg)

        # Load data
        data = pd.read_csv(input_file)
        click.echo(f"Loaded {len(data)} rows, {len(data.columns)} columns")

        # Clean data
        cleaned = cleaner.clean_dataset(data)

        # Save cleaned data
        output_path = cleaner.save_clean_dataset(
            cleaned, topic, source, coverage, start_year, end_year
        )

        # Show transformations
        transformations = cleaner.get_transformations()
        if transformations:
            click.echo("\nTransformations applied:")
            for t in transformations:
                click.echo(f"  • {t}")

        click.echo(f"✅ Cleaned dataset saved to {output_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--topic", required=True, help="Topic name")
@click.option("--source", required=True, help="Source name")
@click.option("--url", help="Original source URL")
@click.option("--force", is_flag=True, help="Force regeneration (ignore cache)")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def document(input_file, topic, source, url, force, config):
    """Generate metadata documentation for a dataset."""
    click.echo(f"📝 Generating metadata for: {input_file}...")

    try:
        cfg = Config(config)
        cleaner = DataCleaner(cfg)
        metadata_gen = MetadataGenerator(cfg)

        # Load data and generate summary
        data = pd.read_csv(input_file)
        data_summary = cleaner.get_data_summary(data)

        # Get transformations if available (empty for existing files)
        transformations = []

        # Generate metadata
        metadata_content = metadata_gen.generate_metadata(
            topic=topic,
            data_summary=data_summary,
            source=source,
            transformations=transformations,
            original_source_url=url,
            force_regenerate=force,
        )

        # Save metadata
        metadata_path = metadata_gen.save_metadata(topic, metadata_content)

        click.echo(f"✅ Metadata saved to {metadata_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--topic", required=True, help="Topic name")
@click.option("--source", required=True, help="Source identifier")
@click.option("--coverage", default="global", help="Geographic coverage")
@click.option("--identifier", help="Optional dataset identifier/slug")
@click.option("--url", help="Original source URL")
@click.option("--min-rows", type=int, help="Validation: minimum rows")
@click.option("--min-columns", type=int, help="Validation: minimum columns")
@click.option("--max-null-percentage", type=float, help="Validation: max null percentage")
@click.option("--min-completeness", type=float, help="Validation: min completeness score")
@click.option("--strict/--no-strict", default=True, help="Fail on validation errors")
@click.option("--ai-package/--no-ai-package", default=True, help="Create AI-ready package files")
@click.option("--rag-index/--no-rag-index", default=False, help="Update RAG catalog index")
@click.option("--force", is_flag=True, help="Force regeneration (ignore cache)")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def pipeline(
    input_file,
    topic,
    source,
    coverage,
    identifier,
    url,
    min_rows,
    min_columns,
    max_null_percentage,
    min_completeness,
    strict,
    ai_package,
    rag_index,
    force,
    config,
):
    """Run full curation pipeline: clean + validate + metadata + package + index."""
    click.echo(f"🔄 Running full pipeline for: {input_file}\n")

    try:
        from src.pipeline import PipelineRunner, PipelineOptions, PipelineValidationConfig

        cfg = Config(config)

        validation = PipelineValidationConfig()
        if min_rows is not None:
            validation.min_rows = min_rows
        if min_columns is not None:
            validation.min_columns = min_columns
        if max_null_percentage is not None:
            validation.max_null_percentage = max_null_percentage
        if min_completeness is not None:
            validation.min_completeness_score = min_completeness

        runner = PipelineRunner(cfg, validation=validation)
        options = PipelineOptions(
            topic=topic,
            source=source,
            coverage=coverage,
            url=url,
            identifier=identifier,
            force=force,
            strict_validation=strict,
            create_ai_package=ai_package,
            rag_index=rag_index,
        )

        manifest = runner.run(Path(input_file), options)

        click.echo("✅ Pipeline complete!")
        click.echo(f"   📊 Data: {manifest.get('output', {}).get('clean_path')}")
        click.echo(f"   📝 Metadata: {manifest.get('metadata_path')}")
        if manifest.get("quality_report_path"):
            click.echo(f"   ✅ Quality: {manifest.get('quality_report_path')}")
        if manifest.get("ai_package"):
            click.echo(f"   🤖 AI package: {manifest.get('ai_package')}")
        if manifest.get("catalog_id"):
            click.echo(f"   🗂️ Catalog ID: {manifest.get('catalog_id')}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--config", default="config.yaml", help="Path to configuration file")
def status(config):
    """Show current status of the data curation project."""
    try:
        cfg = Config(config)

        click.echo("📊 Mises Data Curation - Project Status\n")

        # Check directories
        for dir_type in ["raw", "clean", "metadata", "graphics"]:
            dir_path = cfg.get_directory(dir_type)
            exists = "✅" if dir_path.exists() else "❌"
            click.echo(f"{exists} {dir_type}: {dir_path}")

        # Count files
        clean_dir = cfg.get_directory("clean")
        metadata_dir = cfg.get_directory("metadata")

        if clean_dir.exists():
            csv_files = list(clean_dir.rglob("*.csv"))
            click.echo(f"\n📈 Clean datasets: {len(csv_files)}")

        if metadata_dir.exists():
            md_files = list(metadata_dir.glob("*.md"))
            click.echo(f"📝 Metadata files: {len(md_files)}")

        # Check API keys
        click.echo("\n🔑 API Configuration:")
        llm_config = cfg.get_llm_config()
        click.echo(
            f"  OpenRouter: {'✅ Configured' if llm_config['api_key'] else '❌ Not configured'}"
        )

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--file", "filepath", type=click.Path(exists=True), help="Index a single CSV file"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-index all datasets (ignore change detection)",
)
@click.option("--stats", is_flag=True, help="Show catalog statistics only")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def index(filepath, force, stats, config):
    """Index datasets into SQLite3 catalog for browsing."""
    try:
        cfg = Config(config)
        catalog = DatasetCatalog(cfg)

        # Show statistics only
        if stats:
            click.echo("📊 Dataset Catalog Statistics\n")
            statistics = catalog.get_statistics()
            click.echo(f"Total datasets: {statistics['total_datasets']}")
            click.echo(f"Total size: {statistics['total_size_mb']:.2f} MB")
            click.echo(f"Average completeness: {statistics['avg_completeness']:.1%}")
            click.echo(f"\nBy source:")
            for source, count in statistics["by_source"].items():
                click.echo(f"  {source}: {count}")
            click.echo(f"\nBy topic:")
            for topic, count in statistics["by_topic"].items():
                click.echo(f"  {topic}: {count}")
            return

        # Index single file
        if filepath:
            click.echo(f"📇 Indexing file: {filepath}...")
            file_path = Path(filepath)
            result = catalog.index_dataset(file_path, force=force)

            if result:
                click.echo(f"✅ Indexed successfully! (Dataset ID: {result})")
            else:
                click.echo(f"❌ Failed to index file")

            return

        # Index all datasets
        click.echo("📇 Indexing all datasets in 02_Datasets_Limpios/...\n")
        stats = catalog.index_all(force=force)

        click.echo(f"✅ Indexing complete!\n")
        click.echo(f"   Indexed: {stats['indexed']}")
        click.echo(f"   Skipped: {stats['skipped']} (no changes)")
        click.echo(f"   Errors: {stats['errors']}")

        # Show summary statistics
        click.echo(f"\n📊 Catalog Summary:")
        summary = catalog.get_statistics()
        click.echo(f"   Total datasets: {summary['total_datasets']}")
        click.echo(f"   Database size: {summary['total_size_mb']:.2f} MB")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()



@cli.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option(
    "--type",
    "analysis_type",
    type=click.Choice(["descriptive", "regression", "panel", "compare"]),
    default="descriptive",
    help="Type of analysis to perform",
)
@click.option("--formula", help="Formula for regression or panel models (e.g. 'y ~ x1 + x2')")
@click.option("--group-col", help="Column for group comparison")
@click.option("--value-col", help="Value column for comparison")
@click.option("--entity-col", help="Entity column for panel data (e.g. country)")
@click.option("--time-col", help="Time column for panel data (e.g. year)")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def analyze(
    filepath,
    analysis_type,
    formula,
    group_col,
    value_col,
    entity_col,
    time_col,
    config,
):
    """
    Perform statistical analysis on a dataset.
    
    Supports:
    - Descriptive statistics (default)
    - Group comparisons (t-test, ANOVA)
    - OLS Regression
    - Panel Data Fixed Effects
    """
    from .analysis import analyze_dataset
    
    click.echo(f"📊 Running {analysis_type} analysis on {filepath}...")
    
    try:
        results = analyze_dataset(
            filepath=filepath,
            analysis_type=analysis_type,
            formula=formula,
            group_col=group_col,
            value_col=value_col,
            entity_col=entity_col,
            time_col=time_col
        )
        
        if "error" in results:
            click.echo(f"❌ Error: {results['error']}", err=True)
            return

        click.echo("\n📈 Results:\n")
        
        if analysis_type == "descriptive":
            # Pretty print summary dataframe
            df_summary = pd.DataFrame(results["summary"])
            click.echo(df_summary.to_string())
            
        elif analysis_type == "compare":
             click.echo(f"Test: {results['test']}")
             click.echo(f"Statistic: {results['statistic']:.4f}")
             click.echo(f"P-value: {results['p_value']:.4f}")
             click.echo(f"Significant (p<0.05): {'YES' if results['significant_05'] else 'NO'}")
             
        elif analysis_type in ["regression", "panel"]:
             click.echo(results.get("summary", "No summary available"))
             
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        raise click.Abort()


# =============================================================================
# Agent Commands (Data Formulator-inspired)
# =============================================================================

@cli.group()
def agent():
    """AI-powered data analysis agents."""
    pass


@agent.command("quality")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--fix", is_flag=True, help="Auto-fix detected issues")
@click.option("--strategy", type=click.Choice(["auto", "drop", "mean", "median", "mode"]), 
              default="auto", help="Null value handling strategy")
@click.option("--output", "-o", type=click.Path(), help="Output file for cleaned data")
def agent_quality(filepath, fix, strategy, output):
    """
    Analyze data quality and optionally fix issues.
    
    Examples:
        curate agent quality data.csv
        curate agent quality data.csv --fix --strategy median
        curate agent quality data.csv --fix -o cleaned.csv
    """
    from src.agents import DataCleanAgent, quick_quality_check
    
    click.echo(f"🔍 Analyzing data quality: {filepath}\n")
    
    try:
        data = pd.read_csv(filepath)
        name = Path(filepath).stem
        
        # Run quality check
        report = quick_quality_check(data, name)
        
        # Display results
        click.echo(f"📊 Dataset: {name}")
        click.echo(f"   Filas: {report['total_filas']:,}")
        click.echo(f"   Columnas: {report['total_columnas']}")
        click.echo(f"   Calidad General: {report['calidad_general'].upper()}\n")
        
        if report['issues']:
            click.echo("⚠️  Problemas Detectados:\n")
            for issue in report['issues']:
                severity_icon = "🔴" if issue['severidad'] == "alta" else ("🟡" if issue['severidad'] == "media" else "🟢")
                click.echo(f"   {severity_icon} [{issue['tipo']}] {issue['columna'] or 'General'}")
                click.echo(f"      {issue['descripcion']}")
                click.echo(f"      💡 {issue['solucion_propuesta']}\n")
        else:
            click.echo("✅ No se detectaron problemas significativos\n")
        
        # Fix issues if requested
        if fix:
            click.echo(f"🔧 Aplicando correcciones (estrategia: {strategy})...")
            
            agent = DataCleanAgent()
            cleaned = agent.clean_nulls(data, strategy=strategy)
            cleaned = agent.remove_duplicates(cleaned)
            
            rows_removed = len(data) - len(cleaned)
            click.echo(f"   Filas originales: {len(data):,}")
            click.echo(f"   Filas finales: {len(cleaned):,}")
            click.echo(f"   Filas eliminadas: {rows_removed:,}")
            
            # Save if output specified
            if output:
                cleaned.to_csv(output, index=False)
                click.echo(f"\n✅ Datos limpios guardados en: {output}")
            else:
                # Show preview
                click.echo("\n📋 Vista previa (primeras 5 filas):")
                click.echo(cleaned.head().to_string())
                click.echo("\n💡 Usa --output/-o para guardar los resultados")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@agent.command("report")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--topic", "-t", default=None, help="Report topic/title")
@click.option("--output", "-o", type=click.Path(), help="Output file (markdown)")
def agent_report(filepath, topic, output):
    """
    Generate an analysis report for a dataset.
    
    Examples:
        curate agent report pib_latam.csv
        curate agent report data.csv --topic "Análisis PIB" -o report.md
    """
    from src.agents import quick_report
    
    click.echo(f"📝 Generating report: {filepath}\n")
    
    try:
        data = pd.read_csv(filepath)
        name = Path(filepath).stem
        report_topic = topic or f"Análisis de {name}"
        
        # Generate report
        report_md = quick_report(data, report_topic)
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(report_md)
            click.echo(f"✅ Reporte guardado en: {output}")
        else:
            click.echo(report_md)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@agent.command("transform")
@click.argument("filepath", type=click.Path(exists=True))
@click.argument("goal")
@click.option("--mode", type=click.Choice(["python", "sql"]), default="python", 
              help="Transformation mode")
@click.option("--execute", is_flag=True, default=True, help="Execute generated code")
@click.option("--output", "-o", type=click.Path(), help="Output file for transformed data")
@click.option("--show-code", is_flag=True, help="Show generated code")
def agent_transform(filepath, goal, mode, execute, output, show_code):
    """
    Transform data using natural language.
    
    Examples:
        curate agent transform data.csv "Calcular promedio por país"
        curate agent transform data.csv "Filtrar solo años 2020-2023" --show-code
        curate agent transform data.csv "SELECT pais, AVG(pib) FROM df GROUP BY pais" --mode sql
    """
    from src.agents import DataTransformAgent, SQLTransformAgent, create_table_context
    
    click.echo(f"🔄 Transforming: {filepath}")
    click.echo(f"   Goal: {goal}")
    click.echo(f"   Mode: {mode.upper()}\n")
    
    try:
        data = pd.read_csv(filepath)
        name = Path(filepath).stem
        table_ctx = create_table_context(data, name)
        
        # Create agent
        if mode == "sql":
            agent = SQLTransformAgent(language="es")
        else:
            agent = DataTransformAgent(language="es")
        
        # Run transformation
        click.echo("⏳ Generando transformación...")
        response = agent.transform(goal, [table_ctx], execute=execute)
        
        if response.status != "ok":
            click.echo(f"❌ Error: {response.error}", err=True)
            raise click.Abort()
        
        # Show code if requested
        if show_code and response.code:
            click.echo(f"\n📜 Código generado ({mode.upper()}):\n")
            click.echo("─" * 40)
            click.echo(response.code)
            click.echo("─" * 40 + "\n")
        
        # Show results
        if response.result_data is not None:
            result_df = response.result_data
            click.echo(f"✅ Transformación exitosa!")
            click.echo(f"   Filas resultado: {len(result_df):,}")
            click.echo(f"   Columnas: {list(result_df.columns)}\n")
            
            if output:
                result_df.to_csv(output, index=False)
                click.echo(f"📁 Guardado en: {output}")
            else:
                click.echo("📋 Vista previa:")
                click.echo(result_df.head(10).to_string())
                click.echo("\n💡 Usa --output/-o para guardar los resultados")
        else:
            click.echo("⚠️  No se generaron resultados (execute=False o error)")
            if response.code:
                click.echo("\nCódigo generado:")
                click.echo(response.code)
        
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@agent.command("explore")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--focus", "-f", default=None, help="Focus area for suggestions")
def agent_explore(filepath, focus):
    """
    Get exploration suggestions for a dataset.
    
    Examples:
        curate agent explore pib_latam.csv
        curate agent explore data.csv --focus "tendencias temporales"
    """
    from src.agents import ExplorationAgent, create_table_context
    
    click.echo(f"🔭 Exploring: {filepath}\n")
    
    try:
        data = pd.read_csv(filepath)
        name = Path(filepath).stem
        table_ctx = create_table_context(data, name)
        
        agent = ExplorationAgent(language="es")
        suggestions = agent.get_suggestions_list([table_ctx])
        
        if suggestions:
            click.echo("💡 Sugerencias de Análisis:\n")
            for i, sug in enumerate(suggestions, 1):
                tipo = sug.get('tipo', sug.get('type', 'general'))
                pregunta = sug.get('pregunta', sug.get('question', str(sug)))
                razon = sug.get('razon', sug.get('reason', ''))
                
                click.echo(f"   {i}. [{tipo.upper()}] {pregunta}")
                if razon:
                    click.echo(f"      → {razon}")
                click.echo()
        else:
            click.echo("⚠️  No se generaron sugerencias")
            click.echo("   Esto puede ocurrir si el LLM no está configurado.")
            click.echo("   Las sugerencias requieren conexión a un modelo de lenguaje.")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@agent.command("workflow")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--clean/--no-clean", default=True, help="Include data cleaning step")
@click.option("--report/--no-report", default=True, help="Generate final report")
@click.option("--output", "-o", type=click.Path(), help="Output file for cleaned data")
@click.option("--report-output", "-r", type=click.Path(), help="Output file for report")
def agent_workflow(filepath, clean, report, output, report_output):
    """
    Run complete analysis workflow on a dataset.
    
    Steps: Quality Check → Clean (optional) → Explore → Report (optional)
    
    Examples:
        curate agent workflow data.csv
        curate agent workflow data.csv --no-clean
        curate agent workflow data.csv -o cleaned.csv -r report.md
    """
    from src.agents import AgentOrchestrator
    
    click.echo(f"🔄 Running workflow: {filepath}\n")
    
    try:
        data = pd.read_csv(filepath)
        name = Path(filepath).stem
        
        orchestrator = AgentOrchestrator(language="es")
        
        click.echo("⏳ Ejecutando workflow...")
        result = orchestrator.analyze_dataset(
            data, name,
            clean_data=clean,
            generate_report=report
        )
        
        click.echo(f"\n{'✅' if result.success else '❌'} Workflow {'completado' if result.success else 'con errores'}\n")
        
        # Show step results
        for step in result.steps:
            icon = "✅" if step.success else "❌"
            click.echo(f"   {icon} {step.step_name}: {step.step_type.value}")
            if step.error:
                click.echo(f"      Error: {step.error}")
            if step.metadata:
                for k, v in step.metadata.items():
                    click.echo(f"      {k}: {v}")
        
        # Save outputs
        if output and result.final_data is not None:
            result.final_data.to_csv(output, index=False)
            click.echo(f"\n📁 Datos guardados en: {output}")
        
        if report_output and result.final_report:
            with open(report_output, 'w', encoding='utf-8') as f:
                f.write(result.final_report)
            click.echo(f"📝 Reporte guardado en: {report_output}")
        
        # Show report preview if generated
        if result.final_report and not report_output:
            click.echo("\n" + "─" * 50)
            click.echo("📝 REPORTE:\n")
            # Show first 30 lines
            lines = result.final_report.split('\n')[:30]
            click.echo('\n'.join(lines))
            if len(result.final_report.split('\n')) > 30:
                click.echo("\n... (truncado, usa -r para guardar completo)")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command("rag-list-models")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def rag_list_models(config):
    """List models from the OpenAI-compatible API (for choosing an embedding model)."""
    try:
        cfg = Config(config)
        rag = cfg.get_rag_config()
        base_url = (rag.get("embedding_base_url") or "").rstrip("/")
        if not base_url:
            click.echo("Set OPENAI_BASE_URL or rag.embedding_base_url in config.", err=True)
            raise click.Abort()
        import os
        import requests
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("EMBEDDING_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        r = requests.get(f"{base_url}/models", headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        models = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(models, list):
            models = list(models) if hasattr(models, "__iter__") else [data]
        click.echo(f"Models at {base_url} ({len(models)}):")
        for m in models:
            mid = m.get("id", m.get("model", m)) if isinstance(m, dict) else m
            if isinstance(mid, dict):
                mid = mid.get("id", str(m))
            flag = "  [embedding?]" if "embed" in str(mid).lower() else ""
            click.echo(f"  {mid}{flag}")
        click.echo("\nUse one of the embedding models in config.yaml → rag.embedding_model or .env EMBEDDING_MODEL")
    except requests.exceptions.HTTPError as e:
        click.echo(f"API error: {e.response.status_code} - {e.response.text[:200]}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command("rag-index")
@click.option("--config", default="config.yaml", help="Path to configuration file")
@click.option("--docs/--no-docs", default=True, help="Index docs/*.md")
@click.option("--catalog/--no-catalog", default=True, help="Index dataset catalog metadata")
@click.option("--tools/--no-tools", default=True, help="Index MCP tool descriptions")
@click.option("--docs-root", type=click.Path(path_type=Path), default=None, help="Root directory for .md files (default: DATA_ROOT/docs)")
def rag_index(config, docs, catalog, tools, docs_root):
    """Build RAG vector index (docs, catalog, tools). Run after updating docs or catalog."""
    try:
        cfg = Config(config)
        from src.rag.index import build_index
        counts = build_index(
            cfg,
            docs_root=docs_root,
            index_docs=docs,
            index_catalog=catalog,
            index_tools=tools,
        )
        click.echo("RAG index built:")
        click.echo(f"  docs: {counts.get('docs', 0)} chunks")
        click.echo(f"  catalog: {counts.get('catalog', 0)} chunks")
        click.echo(f"  tools: {counts.get('tools', 0)} chunks")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
