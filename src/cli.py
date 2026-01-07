"""Command-line interface for the data curation tool."""

import click
from pathlib import Path
import pandas as pd
import sys
import os
from .config import Config
from .ingestion import DataIngestionManager
from .cleaning import DataCleaner
from .metadata import MetadataGenerator
from .searcher import IndicatorSearcher

# Fix Windows encoding for Unicode output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Mises Data Curation Tool - Automate economic data curation workflows."""
    pass


@cli.command()
@click.option('--config', default='config.yaml', help='Path to configuration file')
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
@click.argument('query', required=False)
@click.option('--topic', is_flag=False, flag_value='all', help='Search only in a specific topic')
@click.option('--source', type=click.Choice(['ilostat', 'oecd', 'imf', 'worldbank', 'eclac']), help='Filter by source')
@click.option('--list-topics', is_flag=True, help='List all available topics')
@click.option('--list-sources', is_flag=True, help='List all available sources')
@click.option('-v', '--verbose', is_flag=True, help='Show detailed information')
@click.option('--config', default='config.yaml', help='Path to configuration file')
def search(query, topic, source, list_topics, list_sources, verbose, config):
    """Search for available economic indicators (like 'apt search')."""
    try:
        cfg = Config(config)
        searcher = IndicatorSearcher(cfg)
        
        # List all topics
        if list_topics:
            topics = searcher.list_topics()
            click.echo("📊 Available Topics:\n")
            for t in topics:
                indicators = searcher.search_by_topic(t)
                click.echo(f"  {t:<30} ({len(indicators)} indicators)")
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
        
        # Search by topic
        if topic and topic != 'all':
            results = searcher.search_by_topic(topic)
            click.echo(f"\n🔍 Indicators for topic: {topic}\n")
            click.echo(searcher.format_results_table(results, verbose=verbose))
            return
        
        # General search
        if not query:
            click.echo("Usage: curate search <query> [OPTIONS]")
            click.echo("\nExamples:")
            click.echo("  curate search wage              # Search for wage-related indicators")
            click.echo("  curate search --list-topics     # See all topics")
            click.echo("  curate search --source ilostat  # See ILOSTAT indicators")
            click.echo("  curate search informal -v       # Detailed search results")
            return
        
        results = searcher.search(query)
        
        if results:
            click.echo(f"\n🔍 Search results for '{query}':\n")
            click.echo(searcher.format_results_table(results, verbose=verbose))
            
            if not verbose:
                click.echo("\nUse -v for more details, or:")
                if results:
                    first = results[0]['name']
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
@click.option('--source', type=click.Choice(['manual', 'ilostat', 'oecd', 'imf', 'worldbank', 'eclac']), 
              required=True, help='Data source')
@click.option('--filepath', type=click.Path(exists=True), 
              help='Path to file (for manual uploads)')
@click.option('--indicator', help='Indicator name or code')
@click.option('--dataset', help='Dataset identifier (for OECD)')
@click.option('--database', help='Database identifier (for IMF)')
@click.option('--countries', help='Country codes (comma-separated, e.g., ARG,BRA,CHL)')
@click.option('--start-year', type=int, default=2010, help='Starting year')
@click.option('--end-year', type=int, default=2024, help='Ending year')
@click.option('--config', default='config.yaml', help='Path to configuration file')
def ingest(source, filepath, indicator, dataset, database, countries, start_year, end_year, config):
    """Ingest data from various sources (manual upload or public APIs)."""
    click.echo(f"📥 Ingesting data from {source.upper()}...")
    
    try:
        cfg = Config(config)
        manager = DataIngestionManager(cfg)
        
        # Parse countries list
        country_list = None
        if countries:
            country_list = [c.strip().upper() for c in countries.split(',')]
        
        # Build kwargs based on source
        kwargs = {
            'start_year': start_year,
            'end_year': end_year
        }
        
        if country_list:
            kwargs['countries'] = country_list
        
        if source == 'manual':
            if not filepath:
                raise click.UsageError("--filepath is required for manual uploads")
            kwargs['filepath'] = filepath
        elif source == 'ilostat':
            if not indicator:
                raise click.UsageError("--indicator is required for ILOSTAT")
            kwargs['indicator'] = indicator
        elif source == 'oecd':
            if not dataset:
                raise click.UsageError("--dataset is required for OECD")
            kwargs['dataset'] = dataset
            if indicator:
                kwargs['indicator'] = indicator
        elif source == 'imf':
            if not database or not indicator:
                raise click.UsageError("--database and --indicator are required for IMF")
            kwargs['database'] = database
            kwargs['indicator'] = indicator
        
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
@click.option('--source', type=click.Choice(['ilostat', 'oecd', 'imf', 'worldbank', 'eclac']), 
              required=True, help='Data source (API)')
@click.option('--indicator', help='Indicator name or code')
@click.option('--dataset', help='Dataset identifier (for OECD)')
@click.option('--database', help='Database identifier (for IMF)')
@click.option('--countries', help='Country codes (comma-separated, e.g., ARG,BRA,CHL)')
@click.option('--start-year', type=int, default=2010, help='Starting year')
@click.option('--end-year', type=int, default=2024, help='Ending year')
@click.option('--topic', required=True, help='Topic for organization (e.g., salarios_reales)')
@click.option('--coverage', default='latam', help='Geographic coverage')
@click.option('--url', help='Original source URL for metadata')
@click.option('--config', default='config.yaml', help='Path to configuration file')
def download(source, indicator, dataset, database, countries, start_year, end_year, topic, coverage, url, config):
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
            country_list = [c.strip().upper() for c in countries.split(',')]
        
        # Step 1: DOWNLOAD from API
        click.echo(f"Step 1/3: Downloading from {source.upper()}...")
        
        kwargs = {
            'start_year': start_year,
            'end_year': end_year
        }
        
        if country_list:
            kwargs['countries'] = country_list
        
        if source == 'ilostat':
            if not indicator:
                raise click.UsageError("--indicator is required for ILOSTAT")
            kwargs['indicator'] = indicator
        elif source == 'oecd':
            if not dataset:
                raise click.UsageError("--dataset is required for OECD")
            kwargs['dataset'] = dataset
            if indicator:
                kwargs['indicator'] = indicator
        elif source == 'imf':
            if not database or not indicator:
                raise click.UsageError("--database and --indicator are required for IMF")
            kwargs['database'] = database
            kwargs['indicator'] = indicator
        elif source == 'worldbank':
            if not indicator:
                raise click.UsageError("--indicator is required for World Bank")
            kwargs['indicator'] = indicator
        elif source == 'eclac':
            if not indicator:
                raise click.UsageError("--indicator is required for ECLAC (use as table parameter)")
            kwargs['table'] = indicator
        
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
            original_source_url=url or f"https://{source}.org"
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
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--topic', required=True, help='Topic name (e.g., salarios_reales)')
@click.option('--source', required=True, help='Source identifier (e.g., owid, ilostat)')
@click.option('--coverage', default='global', help='Geographic coverage')
@click.option('--start-year', type=int, help='Starting year (auto-detected if not provided)')
@click.option('--end-year', type=int, help='Ending year (auto-detected if not provided)')
@click.option('--config', default='config.yaml', help='Path to configuration file')
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
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--topic', required=True, help='Topic name')
@click.option('--source', required=True, help='Source name')
@click.option('--url', help='Original source URL')
@click.option('--force', is_flag=True, help='Force regeneration (ignore cache)')
@click.option('--config', default='config.yaml', help='Path to configuration file')
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
            force_regenerate=force
        )
        
        # Save metadata
        metadata_path = metadata_gen.save_metadata(topic, metadata_content)
        
        click.echo(f"✅ Metadata saved to {metadata_path}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--topic', required=True, help='Topic name')
@click.option('--source', required=True, help='Source identifier')
@click.option('--coverage', default='global', help='Geographic coverage')
@click.option('--url', help='Original source URL')
@click.option('--config', default='config.yaml', help='Path to configuration file')
def pipeline(input_file, topic, source, coverage, url, config):
    """Run full curation pipeline: clean + document."""
    click.echo(f"🔄 Running full pipeline for: {input_file}\n")
    
    try:
        cfg = Config(config)
        cleaner = DataCleaner(cfg)
        metadata_gen = MetadataGenerator(cfg)
        
        # Step 1: Clean
        click.echo("Step 1/2: Cleaning data...")
        data = pd.read_csv(input_file)
        cleaned = cleaner.clean_dataset(data)
        output_path = cleaner.save_clean_dataset(cleaned, topic, source, coverage)
        transformations = cleaner.get_transformations()
        
        # Step 2: Document
        click.echo("\nStep 2/2: Generating metadata...")
        data_summary = cleaner.get_data_summary(cleaned)
        metadata_content = metadata_gen.generate_metadata(
            topic=topic,
            data_summary=data_summary,
            source=source,
            transformations=transformations,
            original_source_url=url
        )
        metadata_path = metadata_gen.save_metadata(topic, metadata_content)
        
        click.echo(f"\n✅ Pipeline complete!")
        click.echo(f"   📊 Data: {output_path}")
        click.echo(f"   📝 Metadata: {metadata_path}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--config', default='config.yaml', help='Path to configuration file')
def status(config):
    """Show current status of the data curation project."""
    try:
        cfg = Config(config)
        
        click.echo("📊 Mises Data Curation - Project Status\n")
        
        # Check directories
        for dir_type in ['raw', 'clean', 'metadata', 'graphics']:
            dir_path = cfg.get_directory(dir_type)
            exists = "✅" if dir_path.exists() else "❌"
            click.echo(f"{exists} {dir_type}: {dir_path}")
        
        # Count files
        clean_dir = cfg.get_directory('clean')
        metadata_dir = cfg.get_directory('metadata')
        
        if clean_dir.exists():
            csv_files = list(clean_dir.rglob('*.csv'))
            click.echo(f"\n📈 Clean datasets: {len(csv_files)}")
        
        if metadata_dir.exists():
            md_files = list(metadata_dir.glob('*.md'))
            click.echo(f"📝 Metadata files: {len(md_files)}")
        
        # Check API keys
        click.echo("\n🔑 API Configuration:")
        llm_config = cfg.get_llm_config()
        click.echo(f"  OpenRouter: {'✅ Configured' if llm_config['api_key'] else '❌ Not configured'}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
